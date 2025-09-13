import importlib
import time
import os
import argparse
from datetime import datetime
from experiments import metrics_reporter as mr
import threading

def run_experiment(load_type, namespace, label_selector, duration, load_args, phases=None):
    print(f"[INFO] Iniciando experimento com carga: {load_type}")

    if load_type == "selenium":
        load_module = importlib.import_module("experiments.selenium_load")
    elif load_type == "requests":
        # Feature deprecada: requests_load removido
        raise NotImplementedError("O tipo de carga 'requests' foi removido. Use 'selenium'.")
    else:
        raise ValueError("Tipo de carga inválido. Use 'selenium'.")

    events_samples = []

    # Função de monitoramento
    def monitor_metrics():
        mr.collect_during_test(
            namespace=namespace,
            deployment_name="flask-api",
            duration_seconds=max(duration, 20),
            interval_seconds=1,
            shared_events=events_samples  # 👈 passa a lista já existente
        )


    # Inicia thread de monitoramento **antes** do load test
    monitor_thread = threading.Thread(target=monitor_metrics)
    monitor_thread.start()

    # Pequena espera para garantir que coleta começou
    time.sleep(1)

    # Executa teste de carga na thread principal
    start_time = time.time()
    all_latencies, total_success, total_count = [], 0, 0

    driver = None
    if load_type == "selenium":
        driver = load_module.create_driver(load_args["url"])  # cria driver 1 vez

    try:
        # Executa fases de carga
        if phases:
            for i, phase in enumerate(phases, 1):
                
                events_samples.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "event_type": "phase_change",
                    "replica_count": "",
                    "pod_name": "",
                    "cpu_m": "",
                    "cpu_pct": "",
                    "notes": f"Início da Fase {i}"
                })

                print(f"[INFO] Executando fase {i}: {phase}")
                if load_type == "selenium":
                    phase_latencies, phase_success, phase_total = load_module.run_load_test(
                        driver=driver, **{**load_args, **phase}
                    )
                else:
                    phase_latencies, phase_success, phase_total = load_module.run_load_test(**{**load_args, **phase})

                all_latencies.extend(phase_latencies)
                total_success += phase_success
                total_count += phase_total
                print(f"[INFO] Fase {i} concluída. Sucesso={phase_success}/{phase_total}")
                time.sleep(20)  # pequena pausa entre fases
        else:
            if load_type == "selenium":
                latencies, success_count, count = load_module.run_load_test(driver=driver, **load_args)
            else:
                latencies, success_count, count = load_module.run_load_test(**load_args)

            all_latencies.extend(latencies)
            total_success, total_count = success_count, count

    finally:
        if driver:
            driver.quit()  # fecha driver só no final

    end_time = time.time()

    monitor_thread.join()

    print(f"[DEBUG] Total de eventos coletados: {len(events_samples)}")

    # Monta métricas finais
    metrics = {
        "start_time": start_time,
        "end_time": end_time,
        "duration_sec": end_time - start_time,
        "latency_stats": mr.calculate_latency_stats(all_latencies),
        "success_error_rate": mr.calculate_success_rate(total_success, total_count),
        "k8s_usage": mr.get_k8s_resource_usage(namespace, label_selector),
        "total_requests": total_count,
        "total_success": total_success,
        "total_errors": total_count - total_success
    }

    # Salva resultados
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mr.save_metrics_json(metrics, prefix=f"results/metrics_{load_type}")
    mr.save_metrics_csv(events_samples, f"results/k8s_samples_{load_type}_{timestamp}.csv")

    print(f"[INFO] Experimento concluído.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["onprem", "cloud"], required=True, help="Ambiente de execução")
    parser.add_argument("--autoscaling", choices=["true", "false"], required=True, help="HPA ativo ou não")
    parser.add_argument("--load_type", choices=["requests", "selenium"], required=True, help="Tipo de teste de carga")
    parser.add_argument("--namespace", default="default", help="Namespace do Kubernetes")
    parser.add_argument("--label_selector", default="app=flask-api", help="Label selector dos pods")
    parser.add_argument("--duration", type=int, default=600, help="Duração do teste em segundos")

    parser.add_argument("--url", required=True, help="URL alvo da API ou aplicação")
    parser.add_argument("--total", type=int, default=500, help="[requests] Total de requisições")
    parser.add_argument("--concurrency", type=int, default=20, help="[requests] Número de threads")
    parser.add_argument("--image", help="[selenium] Caminho para imagem de teste")
    parser.add_argument("--n", type=int, default=100, help="[selenium] Número de envios")
    parser.add_argument("--sleep", type=float, default=0.1, help="[selenium] Intervalo entre envios")

    args = parser.parse_args()

    if args.load_type == "requests":
        base_args = {"url": args.url, "total": args.total, "concurrency": args.concurrency}
    else:  # selenium
        if not args.image:
            parser.error("--image é obrigatório para load_type=selenium")
        base_args = {"url": args.url, "image_path": args.image, "n": args.n, "sleep": args.sleep}

    phases = [
        #{"n": 200, "sleep": 0.05},   # carga média
        #{"n": 400, "sleep": 0.04},   # carga média alta
        #{"n": 600, "sleep": 0.03},  # carga alta
        {"n": 2000, "sleep": 0.01},  # pico
        {"n": 600, "sleep": 0.03},  # carga alta
        {"n": 50, "sleep": 0.5},     # muito baixo
        {"n": 2000, "sleep": 0.01},  # pico
        {"n": 400, "sleep": 0.04},   # carga média alta
        #{"n": 50, "sleep": 0.2},     # sustentada baixa
    ] if args.load_type == "selenium" else None

    
    '''
    phases = [
        {"n": 2000, "sleep": 0.01},  # pico
        {"n": 400, "sleep": 0.04},   # carga média alta
        {"n": 200, "sleep": 0.05},   # carga média
        {"n": 400, "sleep": 0.04},   # carga média alta
        {"n": 50, "sleep": 0.2}     # sustentada baixa
    ]   # em 300s
    '''

    run_experiment(
        load_type=args.load_type,
        namespace=args.namespace,
        label_selector=args.label_selector,
        duration=args.duration,
        load_args=base_args,
        phases=phases
    )
