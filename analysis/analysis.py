import pandas as pd
import matplotlib.pyplot as plt

# Carregar dados
with_hpa = pd.read_csv("analysis/k8s_samples_selenium_20250914_185903.csv")
without_hpa = pd.read_csv("analysis/k8s_samples_selenium_20250914_195420.csv")

# Ajustar tempo relativo
for df in [with_hpa, without_hpa]:
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["time_s"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds()
    df["cpu_pct"] = df["cpu_pct"].clip(upper=100)  # limita em 100%

# --- Gráfico sem HPA ---
plt.figure(figsize=(12,5))
plt.plot(without_hpa["time_s"], without_hpa["cpu_pct"], label="CPU Pod Único")
plt.title("Cenário sem HPA - Consumo de CPU (%)")
plt.xlabel("Tempo (s)")
plt.ylabel("CPU (%)")
plt.legend()
plt.savefig("analysis/sem_hpa_cpu.png", dpi=300, bbox_inches="tight")
plt.close()

# --- Gráfico com HPA (por pod) ---
plt.figure(figsize=(12,6))
for pod, group in with_hpa.groupby("pod_name"):
    plt.plot(group["time_s"], group["cpu_pct"], label=pod)

plt.title("Cenário com HPA - Consumo de CPU por Pod (%)")
plt.xlabel("Tempo (s)")
plt.ylabel("CPU (%)")
plt.legend()
plt.savefig("analysis/com_hpa_cpu_pods.png", dpi=300, bbox_inches="tight")
plt.close()

# --- Gráfico de evolução do número de pods ---
plt.figure(figsize=(12,4))
plt.step(with_hpa["time_s"], with_hpa["replica_count"], where="post")
plt.title("Cenário com HPA - Evolução do Número de Pods")
plt.xlabel("Tempo (s)")
plt.ylabel("Número de Pods")
plt.savefig("analysis/com_hpa_replicas.png", dpi=300, bbox_inches="tight")
plt.close()
