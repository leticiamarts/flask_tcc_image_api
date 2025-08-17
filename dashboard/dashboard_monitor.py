import argparse
import datetime
import json
import sys
import time
import csv
from typing import Dict, Any, List, Optional, Set
import os

from kubernetes import client, config


CSV_FIELDS = [
    "timestamp",
    "event_type",
    "replica_count",
    "pod_name",
    "cpu_m",
    "cpu_pct",
    "notes",
]


def parse_args():
    ap = argparse.ArgumentParser(description="Monitor de métricas via metrics.k8s.io")
    ap.add_argument("--namespace", default="default")
    ap.add_argument("--deployment-name", default="flask-api")
    ap.add_argument("--label-selector", default="app=flask-api",
                    help="Seleciona apenas pods do app (ex.: app=flask-api)")
    ap.add_argument("--interval", type=float, default=1.0, help="Intervalo de coleta em segundos")
    ap.add_argument("--duration", type=int, default=0, help="Duração em segundos (0 = até Ctrl+C)")
    ap.add_argument("--scenario", default="", help="Rótulo livre (ex.: sem_hpa / com_hpa)")
    ap.add_argument("--out", default="results/monitor.ndjson", help="Arquivo de saída (NDJSON ou CSV)")
    ap.add_argument("--format", choices=["ndjson", "csv"], default="ndjson")
    return ap.parse_args()


def cpu_to_m(cpu_str: str) -> float:
    s = cpu_str.strip()
    if s.endswith("n"):   # nano cores
        return float(s[:-1]) / 1_000_000.0
    if s.endswith("m"):   # millicores
        return float(s[:-1])
    # cores (sem sufixo)
    return float(s) * 1000.0


def mem_to_mi(mem_str: str) -> float:
    # Apenas para referência; hoje não escrevemos memória no CSV, mas pode ser útil
    s = mem_str.strip().lower()
    try:
        if s.endswith("ki"):
            return float(s[:-2]) / 1024.0
        if s.endswith("mi"):
            return float(s[:-2])
        if s.endswith("gi"):
            return float(s[:-2]) * 1024.0
        if s.endswith("ti"):
            return float(s[:-2]) * 1024.0 * 1024.0
        # bytes sem sufixo -> converte para Mi
        return float(s) / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat()


def write_ndjson_line(fh, obj: Dict[str, Any]):
    fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    fh.flush()


def to_csv_row(evt: Dict[str, Any]) -> Dict[str, Any]:
    row = {k: "" for k in CSV_FIELDS}
    for k in ["timestamp", "event_type", "replica_count", "pod_name", "cpu_m", "cpu_pct", "notes"]:
        if k in evt:
            row[k] = evt[k]
    # compat: se vier avg_cpu_pct
    if not row["cpu_pct"] and "avg_cpu_pct" in evt:
        row["cpu_pct"] = evt["avg_cpu_pct"]
    # se vier replicas_before / replicas_after, anexa ao notes
    if "replicas_before" in evt or "replicas_after" in evt:
        row["notes"] = (row["notes"] + f" replicas {evt.get('replicas_before','')}->{evt.get('replicas_after','')}").strip()
    return row


def main():
    args = parse_args()

    # kubeconfig local ou in-cluster
    config.load_kube_config()

    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    custom_api = client.CustomObjectsApi()

    start_time = time.time()
    end_time = start_time + args.duration if args.duration and args.duration > 0 else None

    
    if args.format == "csv":
        out_fh = open(args.out, "w", newline="", encoding="utf-8")
        csv_writer = csv.DictWriter(out_fh, fieldnames=CSV_FIELDS)
        csv_writer.writeheader()
    else:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        out_fh = open(args.out, "w", encoding="utf-8")
        csv_writer = None

    last_replica_count: Optional[int] = None
    summary = {
        "scenario": args.scenario,
        "first_cpu_alert_ts": None,
        "first_cpu_critical_ts": None,
        "request_wait_count": 0,
        "scale_events": 0,
        "max_cpu_pct_seen": 0.0,
        "samples": 0,
    }

    try:
        while True:
            if end_time is not None and time.time() >= end_time:
                break

            ts = now_iso()

            # 1) Descobre pods do app (pelo label) no namespace
            try:
                pods = v1.list_namespaced_pod(args.namespace, label_selector=args.label_selector)
                selected_pod_names: Set[str] = {p.metadata.name for p in pods.items}
                replica_count = len(selected_pod_names)
            except Exception as e:
                print(f"[WARN] Falha listando pods: {e}", file=sys.stderr)
                time.sleep(args.interval)
                continue

            # 2) Lê métricas de todos os pods do namespace e filtra pelos selecionados
            try:
                metrics = custom_api.list_namespaced_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    namespace=args.namespace,
                    plural="pods"
                )
            except Exception as e:
                print(f"[WARN] Falha lendo metrics.k8s.io: {e}", file=sys.stderr)
                time.sleep(args.interval)
                continue

            cpu_m_list: List[float] = []
            all_100 = True

            for item in metrics.get("items", []):
                pod_name = item["metadata"]["name"]
                if pod_name not in selected_pod_names:
                    continue  # ignora pods fora do label

                try:
                    c = item["containers"][0]["usage"]
                    cpu_m = cpu_to_m(c["cpu"])
                    cpu_pct = (cpu_m / 1000.0) * 100.0

                    cpu_m_list.append(cpu_m)
                    if cpu_pct < 100.0:
                        all_100 = False

                    evt = {
                        "timestamp": ts,
                        "event_type": "pod_usage",
                        "replica_count": replica_count,
                        "pod_name": pod_name,
                        "cpu_m": round(cpu_m, 3),
                        "cpu_pct": cpu_pct,
                        "notes": args.scenario or ""
                    }

                    if args.format == "csv":
                        csv_writer.writerow(to_csv_row(evt))
                        out_fh.flush()
                    else:
                        write_ndjson_line(out_fh, evt)

                    if cpu_pct > summary["max_cpu_pct_seen"]:
                        summary["max_cpu_pct_seen"] = cpu_pct

                except Exception as e:
                    print(f"[WARN] Erro processando pod {pod_name}: {e}", file=sys.stderr)

            # 3) Alertas agregados por média
            if cpu_m_list:
                avg_cpu_m = sum(cpu_m_list) / len(cpu_m_list)
                avg_pct = (avg_cpu_m / 1000.0) * 100.0

                if avg_pct >= 70.0:
                    evt = {
                        "timestamp": ts,
                        "event_type": "cpu_alert",
                        "replica_count": replica_count,
                        "pod_name": "",
                        "cpu_m": "",
                        "cpu_pct": avg_pct,
                        "notes": f"CPU media >= 70% ({args.scenario})"
                    }
                    if args.format == "csv":
                        csv_writer.writerow(to_csv_row(evt))
                        out_fh.flush()
                    else:
                        write_ndjson_line(out_fh, evt)
                    if summary["first_cpu_alert_ts"] is None:
                        summary["first_cpu_alert_ts"] = ts

                if avg_pct >= 100.0:
                    evt = {
                        "timestamp": ts,
                        "event_type": "cpu_critical",
                        "replica_count": replica_count,
                        "pod_name": "",
                        "cpu_m": "",
                        "cpu_pct": avg_pct,
                        "notes": f"CPU media >= 100% ({args.scenario})"
                    }
                    if args.format == "csv":
                        csv_writer.writerow(to_csv_row(evt))
                        out_fh.flush()
                    else:
                        write_ndjson_line(out_fh, evt)
                    if summary["first_cpu_critical_ts"] is None:
                        summary["first_cpu_critical_ts"] = ts

            # 4) Fila (todos os pods ~100%)
            if replica_count > 0 and cpu_m_list and all_100:
                evt = {
                    "timestamp": ts,
                    "event_type": "request_wait",
                    "replica_count": replica_count,
                    "pod_name": "",
                    "cpu_m": "",
                    "cpu_pct": "",
                    "notes": f"Todas as réplicas ~100% ({args.scenario})"
                }
                if args.format == "csv":
                    csv_writer.writerow(to_csv_row(evt))
                    out_fh.flush()
                else:
                    write_ndjson_line(out_fh, evt)
                summary["request_wait_count"] += 1

            # 5) Scale events via Deployment (status.replicas)
            try:
                dep = apps_v1.read_namespaced_deployment(args.deployment_name, args.namespace)
                current_replicas = dep.status.replicas or 0
            except Exception as e:
                print(f"[WARN] Falha lendo deployment: {e}", file=sys.stderr)
                current_replicas = replica_count  # fallback

            if last_replica_count is not None and current_replicas != last_replica_count:
                evt = {
                    "timestamp": ts,
                    "event_type": "scale_event",
                    "replica_count": current_replicas,
                    "replicas_before": last_replica_count,
                    "replicas_after": current_replicas,
                    "pod_name": "",
                    "cpu_m": "",
                    "cpu_pct": "",
                    "notes": f"Replicas alteradas de {last_replica_count} para {current_replicas} ({args.scenario})"
                }
                if args.format == "csv":
                    csv_writer.writerow(to_csv_row(evt))
                    out_fh.flush()
                else:
                    write_ndjson_line(out_fh, evt)
                summary["scale_events"] += 1

            last_replica_count = current_replicas
            summary["samples"] += 1

            time.sleep(max(args.interval, 0.1))

    except KeyboardInterrupt:
        pass
    finally:
        out_fh.close()

        if args.duration and args.duration > 0:
            summary_path = args.out.rsplit(".", 1)[0] + ".summary.json"
            with open(summary_path, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, ensure_ascii=False)
            print(f"[INFO] Resumo salvo em: {summary_path}")


if __name__ == "__main__":
    main()
