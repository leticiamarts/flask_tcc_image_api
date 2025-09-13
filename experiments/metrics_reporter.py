import json
import datetime
import statistics
import subprocess
import csv
import time
from kubernetes import client, config
import logging


CSV_FIELDS = [
    "timestamp",
    "event_type",
    "replica_count",
    "pod_name",
    "cpu_m",
    "cpu_pct",
    "notes",
]

# =========================
# Funções utilitárias
# =========================

def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def save_metrics_json(metrics, prefix="metrics"):
    filename = f"{prefix}_{get_timestamp()}.json"
    with open(filename, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"[INFO] Métricas salvas em {filename}")

def _normalize_event_for_csv(event: dict) -> dict:
    """
    Garante que o evento tenha exatamente as colunas do CSV_FIELDS.
    - Se vier avg_cpu_pct, mapeia para cpu_pct.
    - Se vier replicas_before/replicas_after, anexa ao notes.
    """
    row = {k: "" for k in CSV_FIELDS}
    for k in CSV_FIELDS:
        if k in event:
            row[k] = event[k]

    # Fallback: avg_cpu_pct -> cpu_pct
    if not row["cpu_pct"] and "avg_cpu_pct" in event:
        row["cpu_pct"] = event["avg_cpu_pct"]

    # Preserva info de scaling se existir
    if "replicas_before" in event or "replicas_after" in event:
        before_ = event.get("replicas_before", "")
        after_ = event.get("replicas_after", "")
        extra = f"replicas {before_}->{after_}"
        row["notes"] = (row["notes"] + " " + extra).strip()

    return row

def save_metrics_csv(samples, filename):
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        if samples:
            normalized = [_normalize_event_for_csv(e) for e in samples]
            writer.writerows(normalized)
            print(f"[INFO] CSV de eventos salvo em {filename}")
        else:
            print(f"[INFO] Nenhum evento coletado, CSV vazio criado: {filename}")

# =========================
# Métricas de aplicação
# =========================

def calculate_latency_stats(latencies):
    if not latencies:
        return {}
    return {
        "latency_avg_ms": statistics.mean(latencies),
        "latency_min_ms": min(latencies),
        "latency_max_ms": max(latencies),
        "latency_p50_ms": statistics.quantiles(latencies, n=100)[49],
        "latency_p90_ms": statistics.quantiles(latencies, n=100)[89],
        "latency_p99_ms": statistics.quantiles(latencies, n=100)[98],
    }

def calculate_success_rate(success_count, total_count):
    return {
        "success_rate_pct": (success_count / total_count) * 100 if total_count > 0 else 0,
        "error_rate_pct": (1 - (success_count / total_count)) * 100 if total_count > 0 else 0
    }

# =========================
# Métricas de Kubernetes
# =========================

def get_k8s_metrics_top(namespace=None):
    cmd = ["kubectl", "top", "pods", "--no-headers"]
    if namespace:
        cmd.extend(["-n", namespace])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        total_cpu_m = 0
        total_mem_mi = 0
        pod_count = 0

        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 3:
                cpu = parts[1]
                mem = parts[2]
                cpu_m = int(cpu[:-1]) if cpu.endswith("m") else int(cpu)*1000
                mem_mi = int(mem[:-2])*1024 if mem.lower().endswith("gi") else int(mem[:-2]) if mem.lower().endswith("mi") else int(mem)
                total_cpu_m += cpu_m
                total_mem_mi += mem_mi
                pod_count += 1

        return {
            "cpu_total_m": total_cpu_m,
            "mem_total_mi": total_mem_mi,
            "pod_count": pod_count
        }
    except subprocess.CalledProcessError as e:
        print("Erro ao coletar métricas do Kubernetes:", e)
        return None

def get_k8s_resource_usage(namespace, label_selector):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)
    usage_top = get_k8s_metrics_top(namespace)
    return {
        "replica_count": len(pods.items),
        "cpu_total_m": usage_top["cpu_total_m"] if usage_top else 0,
        "mem_total_mi": usage_top["mem_total_mi"] if usage_top else 0
    }

logging.basicConfig(filename="k8s_test_events.log", level=logging.INFO, format="%(asctime)s - %(message)s")
_last_replica_count = None

# =========================
# Coleta de métricas
# =========================

def collect_snapshot(namespace="default", deployment_name="flask-api"):
    global _last_replica_count
    config.load_kube_config()
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    custom_api = client.CustomObjectsApi()
    events = []
    replicas = None

    try:
        deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
        replicas = deployment.status.replicas or 0
    except Exception as e:
        logging.warning(f"Erro ao obter deployment {deployment_name}: {e}")

    try:
        metrics = custom_api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods"
        )
    except Exception as e:
        logging.warning(f"Erro ao coletar métricas: {e}")
        return []

    cpu_totals = []
    all_pods_100 = True

    for pod in metrics.get("items", []):
        pod_name = pod["metadata"]["name"]
        try:
            cpu_usage_str = pod["containers"][0]["usage"]["cpu"]
            if cpu_usage_str.endswith("n"):
                cpu_millicores = int(cpu_usage_str[:-1]) / 1_000_000
            elif cpu_usage_str.endswith("m"):
                cpu_millicores = int(cpu_usage_str[:-1])
            else:
                cpu_millicores = int(cpu_usage_str) * 1000

            cpu_pct = (cpu_millicores / 1000) * 100
            cpu_totals.append(cpu_millicores)
            if cpu_pct < 100:
                all_pods_100 = False

            events.append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "event_type": "pod_usage",
                "replica_count": replicas,
                "pod_name": pod_name,
                "cpu_m": cpu_millicores,
                "cpu_pct": cpu_pct,
                "notes": ""
            })
        except Exception as e:
            logging.warning(f"Erro ao processar CPU do pod {pod_name}: {e}")

    if _last_replica_count is not None and replicas is not None and replicas != _last_replica_count:
        events.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "event_type": "scale_event",
            "replica_count": replicas,
            "replicas_before": _last_replica_count,
            "replicas_after": replicas,
            "pod_name": "",
            "cpu_m": "",
            "cpu_pct": "",
            "notes": f"Replicas alteradas de {_last_replica_count} para {replicas}"
        })
    _last_replica_count = replicas

    if cpu_totals:
        avg_cpu_m = sum(cpu_totals) / len(cpu_totals)
        cpu_pct_avg = (avg_cpu_m / 1000) * 100
        if cpu_pct_avg >= 70:
            events.append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "event_type": "cpu_alert",
                "replica_count": replicas,
                "pod_name": "",
                "cpu_m": "",
                "cpu_pct": cpu_pct_avg,
                "notes": "CPU media >=70%"
            })
        if cpu_pct_avg >= 100:
            events.append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "event_type": "cpu_critical",
                "replica_count": replicas,
                "pod_name": "",
                "cpu_m": "",
                "cpu_pct": cpu_pct_avg,
                "notes": "CPU media >=100%"
            })

    if replicas and replicas > 0 and all_pods_100:
        events.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "event_type": "request_wait",
            "replica_count": replicas,
            "pod_name": "",
            "cpu_m": "",
            "cpu_pct": "",
            "notes": "Todas réplicas saturadas, requests podem estar aguardando CPU"
        })

    return events


def collect_during_test(namespace="default", deployment_name="flask-api",
                        duration_seconds=60, interval_seconds=5,
                        shared_events=None):
    """
    Monitora métricas de CPU e eventos durante o teste.
    """
    start_time = time.time()
    events = shared_events if shared_events is not None else []
    logging.info("Iniciando coleta de métricas durante teste.")

    while time.time() - start_time < duration_seconds:
        snapshot_events = collect_snapshot(namespace, deployment_name)
        events.extend(snapshot_events)
        time.sleep(interval_seconds)
    
    print(f"[DEBUG] Total de eventos coletados: {len(events)}")
    return events

