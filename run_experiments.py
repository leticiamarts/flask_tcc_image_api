import importlib
import time
import os
import argparse
from datetime import datetime
from experiments import metrics_reporter as mr
import threading
from concurrent.futures import ThreadPoolExecutor


from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib

def run_phase_in_parallel(load_module, phase, load_args, threads=4):
    all_latencies, total_success, total_count = [], 0, 0

    def run_thread_load():
        # cada thread cria seu próprio driver
        driver = load_module.create_driver(load_args["url"])
        try:
            latencies, success, count = load_module.run_load_test(
                driver=driver, **{**load_args, **phase}
            )
            return latencies, success, count
        except Exception as e:
            print(f"[ERROR] Thread load falhou: {e}")
            return [], 0, 0
        finally:
            driver.quit()  # garante que só a thread que criou fecha

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(run_thread_load) for _ in range(threads)]
        for f in as_completed(futures):
            lat, success, count = f.result()
            all_latencies.extend(lat)
            total_success += success
            total_count += count

    return all_latencies, total_success, total_count



def run_experiment(load_type, namespace, label_selector, duration, load_args, phases=None, threads=3):
    print(f"[INFO] Iniciando experimento com carga: {load_type}")

    if load_type == "selenium":
        load_module = importlib.import_module("experiments.selenium_load")
    else:
        raise ValueError("Tipo de carga inválido. Use 'selenium'.")

    events_samples = []

    # Função de monitoramento
    def monitor_metrics():
        nonlocal events_samples
        events_samples = mr.collect_during_test(
            namespace=namespace,
            deployment_name="flask-api",
            duration_seconds=max(duration, 20),
            interval_seconds=1,
            use_kubelet=True
        )

    # Inicia thread de monitoramento **antes** do load test
    monitor_thread = threading.Thread(target=monitor_metrics)
    monitor_thread.start()
    time.sleep(1)

    start_time = time.time()
    all_latencies, total_success, total_count = [], 0, 0

    try:
        if phases:
            for i, phase in enumerate(phases, 1):
                print(f"[INFO] Executando fase {i}: {phase}")
                phase_latencies, phase_success, phase_total = run_phase_in_parallel(load_module, phase, load_args, threads=threads)
                all_latencies.extend(phase_latencies)
                total_success += phase_success
                total_count += phase_total
                print(f"[INFO] Fase {i} concluída. Sucesso={phase_success}/{phase_total}")
        else:
            all_latencies, total_success, total_count = load_module.run_load_test(**load_args)

    finally:
        monitor_thread.join()

    end_time = time.time()

    timestamp_str = mr.get_timestamp()
    mr.save_raw_json(events_samples, f"results/k8s_raw_{load_type}_{timestamp_str}.json")
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
    parser.add_argument("--duration", type=int, default=240, help="Duração do teste em segundos")

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
        {"n": 1000, "sleep": 0.1},  # pico
        {"n": 600, "sleep": 0.05}#,   # carga média alta
        #{"n": 200, "sleep": 0.05},   # carga média
        #{"n": 400, "sleep": 0.04},   # carga média alta
        #{"n": 50, "sleep": 0.2}     # sustentada baixa
    ] if args.load_type == "selenium" else None

    run_experiment(
        load_type=args.load_type,
        namespace=args.namespace,
        label_selector=args.label_selector,
        duration=args.duration,
        load_args=base_args,
        phases=phases
    )