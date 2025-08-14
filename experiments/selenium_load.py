import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True, help="URL pública da aplicação Streamlit")
parser.add_argument("--image", required=True, help="Caminho para imagem de teste")
parser.add_argument("--n", type=int, default=100, help="Número de envios")
parser.add_argument("--sleep", type=float, default=0.1, help="Intervalo entre envios")
args, _ = parser.parse_known_args()

def run_load_test(url, image_path, n=100, sleep=0.1):
    driver = webdriver.Chrome()
    driver.get(url)
    driver.set_script_timeout(1)

    latencies = []
    success_count = 0
    total_count = n

    try:
        # Fecha popup inicial se existir
        try:
            WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Visit Site')]"))
            ).click()
            print("Popup fechado")
        except:
            pass

        # Envia arquivo
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
                elapsed_ms = (time.time() - start) * 1000
                latencies.append(elapsed_ms)
                success_count += 1
            except:
                latencies.append((time.time() - start) * 1000)
            time.sleep(sleep)

    finally:
        driver.quit()

    return latencies, success_count, total_count


if __name__ == "__main__":
    latencies, success, total = run_load_test()
    print(f"Total Requests: {total}, Success: {success}")
    print(f"Average Latency: {sum(latencies)/len(latencies):.2f} ms")



