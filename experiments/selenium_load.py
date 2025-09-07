import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime
import json
from kubernetes import client, config
import csv

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True, help="URL pública da aplicação Streamlit")
parser.add_argument("--image", required=True, help="Caminho para imagem de teste")
parser.add_argument("--n", type=int, default=100, help="Número de envios")
parser.add_argument("--sleep", type=float, default=0.1, help="Intervalo entre envios")
args, _ = parser.parse_known_args()

# =========================
# Helpers Kubernetes / Logging
# =========================
def check_hpa_status(namespace="default", deployment_name="flask-api"):
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    replicas = deployment.status.replicas or 0
    available = deployment.status.available_replicas or 0
    return replicas, available

def save_selenium_hpa_events(events, prefix="results/selenium_hpa_events"):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"{prefix}_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(events, f, indent=4)
    print(f"[INFO] Selenium HPA events salvos em {json_file}")

    csv_file = f"{prefix}_{timestamp}.csv"
    if events:
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(events[0].keys()))
            writer.writeheader()
            writer.writerows(events)
        print(f"[INFO] Selenium HPA events CSV salvo em {csv_file}")

# =========================
# Driver Management
# =========================
def create_driver(url):
    driver = webdriver.Chrome()
    driver.get(url)
    driver.set_script_timeout(1)
    # fecha popup inicial se existir
    try:
        WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Visit Site')]"))
        ).click()
        print("Popup fechado")
    except:
        pass
    return driver

# =========================
# Teste de carga Selenium
# =========================
def run_load_test(url, image_path, n=100, sleep=0.1, driver=None):
    created_here = False
    if driver is None:
        driver = create_driver(url)
        created_here = True

    latencies = []
    success_count = 0
    total_count = n
    hpa_events = []

    try:
        upload = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
        )
        upload.send_keys(image_path)

        send_btn = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//button[contains(., "Enviar")]'))
        )

        for i in range(n):
            start = time.time()
            try:
                driver.execute_script("arguments[0].click();", send_btn)

                processed_img = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
                )

                elapsed_ms = (time.time() - start) * 1000
                latencies.append(elapsed_ms)
                success_count += 1
            except:
                elapsed_ms = (time.time() - start) * 1000
                latencies.append(elapsed_ms)
                print(f"[WARN] Request {i+1} falhou: {e}")
                

            replicas, available = check_hpa_status()
            hpa_events.append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "click_index": i+1,
                "latency_ms": elapsed_ms,
                "replicas": replicas,
                "available_replicas": available,
                "status": "ok" if replicas == available else "waiting",
                "notes": "HPA disparado, pods não prontos" if replicas > available else ""
            })

            time.sleep(sleep)

    finally:
        if created_here:
            driver.quit()
            save_selenium_hpa_events(hpa_events)

    return latencies, success_count, total_count

if __name__ == "__main__":
    latencies, success, total = run_load_test(args.url, args.image, args.n, args.sleep)
    print(f"Total Requests: {total}, Success: {success}")
    print(f"Average Latency: {sum(latencies)/len(latencies):.2f} ms")
