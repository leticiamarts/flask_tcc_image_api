import json

path = "results/monitor_sem_hpa.ndjson"
with open(path, "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

# 1) Primeiro timestamp que atingiu 70% (cpu_alert)
first_alert = next((e for e in events if e["event_type"] == "cpu_alert"), None)
print("first cpu_alert:", first_alert)

# 2) Primeiro timestamp que atingiu 100% (cpu_critical)
first_critical = next((e for e in events if e["event_type"] == "cpu_critical"), None)
print("first cpu_critical:", first_critical)

# 3) Quantos request_wait (todos pods ~100%)
rq_waits = [e for e in events if e["event_type"] == "request_wait"]
print("request_wait count:", len(rq_waits))
