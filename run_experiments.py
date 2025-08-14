import importlib
import time
import os
import argparse
from datetime import datetime
from experiments import metrics_reporter as mr

def run_experiment(load_type, namespace, label_selector, duration, load_args):
    print(f"[INFO] Iniciando experimento com carga: {load_type}")

    # Importa o módulo certo
    if load_type == "requests":
        load_module = importlib.import_module("experiments.requests_load")
    elif load_type == "selenium":
        load_module = importlib.import_module("experiments.selenium_load")
    else:
        raise ValueError("Tipo de carga inválido. Use 'requests' ou 'selenium'.")

    # Coleta métricas enquanto a carga roda
    start_time = time.time()
    metrics_samples = mr.collect_during_test(duration, interval=5, namespace=namespace)

    # Executa teste de carga (passando args específicos)
    latencies, success_count, total_count = load_module.run_load_test(**load_args)
    end_time = time.time()

    # Monta métricas finais
    metrics = {
        "start_time": start_time,
        "end_time": end_time,
        "duration_sec": end_time - start_time,
        "latency_stats": mr.calculate_latency_stats(latencies),
        "success_error_rate": mr.calculate_success_rate(success_count, total_count),
        "k8s_usage": mr.get_k8s_resource_usage(namespace, label_selector),
        "total_requests": total_count,
        "total_success": success_count,
        "total_errors": total_count - success_count
    }

    # Salva resultados
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mr.save_metrics_json(metrics, prefix=f"results/metrics_{load_type}")
    mr.save_metrics_csv(metrics_samples, f"results/k8s_samples_{load_type}_{timestamp}.csv")

    print(f"[INFO] Experimento concluído.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["onprem", "cloud"], required=True, help="Ambiente de execução")
    parser.add_argument("--autoscaling", choices=["true", "false"], required=True, help="HPA ativo ou não")
    parser.add_argument("--load_type", choices=["requests", "selenium"], required=True, help="Tipo de teste de carga")
    parser.add_argument("--namespace", default="default", help="Namespace do Kubernetes")
    parser.add_argument("--label_selector", default="app=myapp", help="Label selector dos pods")
    parser.add_argument("--duration", type=int, default=60, help="Duração do teste em segundos")

    # Parâmetros específicos para cada tipo de carga
    parser.add_argument("--url", required=True, help="URL alvo da API ou aplicação")
    parser.add_argument("--total", type=int, default=500, help="[requests] Total de requisições")
    parser.add_argument("--concurrency", type=int, default=20, help="[requests] Número de threads")
    parser.add_argument("--image", help="[selenium] Caminho para imagem de teste")
    parser.add_argument("--n", type=int, default=100, help="[selenium] Número de envios")
    parser.add_argument("--sleep", type=float, default=0.1, help="[selenium] Intervalo entre envios")

    args = parser.parse_args()

    # Monta argumentos específicos para o teste de carga
    if args.load_type == "requests":
        load_args = {
            "url": args.url,
            "total": args.total,
            "concurrency": args.concurrency
        }
    else:  # selenium
        if not args.image:
            parser.error("--image é obrigatório para load_type=selenium")
        load_args = {
            "url": args.url,
            "image_path": args.image,
            "n": args.n,
            "sleep": args.sleep
        }

    run_experiment(
        load_type=args.load_type,
        namespace=args.namespace,
        label_selector=args.label_selector,
        duration=args.duration,
        load_args=load_args
    )

