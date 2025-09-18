import pandas as pd
import matplotlib.pyplot as plt

# Carregar dados
with_hpa = pd.read_csv("analysis/k8s_samples_selenium_20250914_213912.csv")
without_hpa = pd.read_csv("analysis/k8s_samples_selenium_20250914_195420.csv")

# Ajustar tempo relativo
for df in [with_hpa, without_hpa]:
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["time_s"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds()
    df["cpu_pct"] = df["cpu_pct"].clip(upper=100)  # limita em 100%

# Criar figura com dois gráficos empilhados
fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(12, 10), sharex=True)

# --- Gráfico sem HPA ---
axes[0].plot(without_hpa["time_s"], without_hpa["cpu_pct"], label="CPU Pod Único")
axes[0].set_title("Cenário sem HPA - Consumo de CPU (%)")
axes[0].set_ylabel("CPU (%)")
axes[0].legend()

# --- Gráfico com HPA (por pod) ---
for pod, group in with_hpa.groupby("pod_name"):
    axes[1].plot(group["time_s"], group["cpu_pct"], label=pod)

axes[1].set_title("Cenário com HPA - Consumo de CPU por Pod (%)")
axes[1].set_xlabel("Tempo (s)")
axes[1].set_ylabel("CPU (%)")
axes[1].legend()

# Ajustar layout e salvar
plt.tight_layout()
plt.savefig("analysis/comparacao_hpa.png", dpi=300, bbox_inches="tight")
plt.close()
