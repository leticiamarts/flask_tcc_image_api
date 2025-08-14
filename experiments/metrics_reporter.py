import json
import datetime
import statistics
import subprocess
import csv
import time
from kubernetes import client, config

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

def save_metrics_csv(samples, filename):
    if not samples:
        return
    keys = samples[0].keys()
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(samples)

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
    """
    Coleta métricas de pods via `kubectl top pods`.
    Necessita do metrics-server instalado.
    """
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
            parts = line.split()
            if len(parts) >= 3:
                cpu = parts[1]
                mem = parts[2]
                # CPU
                if cpu.endswith("m"):
                    cpu_m = int(cpu[:-1])
                else:
                    cpu_m = int(cpu) * 1000
                # Memória
                if mem.lower().endswith("mi"):
                    mem_mi = int(mem[:-2])
                elif mem.lower().endswith("gi"):
                    mem_mi = int(mem[:-2]) * 1024
                else:
                    mem_mi = int(mem)
                
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
    """
    Lista pods pelo label_selector e retorna contagem de réplicas.
    Coleta CPU/memória total via kubectl top.
    """
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)
    usage_top = get_k8s_metrics_top(namespace)

    return {
        "replica_count": len(pods.items),
        "cpu_total_m": usage_top["cpu_total_m"] if usage_top else 0,
        "mem_total_mi": usage_top["mem_total_mi"] if usage_top else 0
    }

def collect_during_test(duration, interval=5, namespace=None):
    """
    Coleta métricas repetidamente durante o teste.
    """
    samples = []
    start_time = time.time()
    while time.time() - start_time < duration:
        metrics = get_k8s_metrics_top(namespace)
        if metrics:
            metrics["timestamp"] = datetime.datetime.utcnow().isoformat()
            samples.append(metrics)
        time.sleep(interval)
    return samples
