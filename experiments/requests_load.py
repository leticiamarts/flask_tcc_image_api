import argparse
import requests
import concurrent.futures
import time

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True, help="URL da API Flask")
parser.add_argument("--total", type=int, default=500, help="Total de requisições")
parser.add_argument("--concurrency", type=int, default=20, help="Número de threads")
args, _ = parser.parse_known_args()

def run_load_test(url, total=500, concurrency=20, image_path="test_image2.png"):
    latencies = []
    success_count = 0
    total_count = total

    def send_request(_):
        nonlocal latencies
        start = time.time()
        try:
            with open(image_path, "rb") as f:
                r = requests.post(url, files={"file": f}, timeout=5)
            elapsed_ms = (time.time() - start) * 1000
            latencies.append(elapsed_ms)
            return r.status_code == 200
        except:
            latencies.append((time.time() - start) * 1000)
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(send_request, range(total_count)))

    success_count = sum(results)
    return latencies, success_count, total_count

if __name__ == "__main__":
    latencies, success, total = run_load_test()
    print(f"Total Requests: {total}, Success: {success}")
    print(f"Average Latency: {sum(latencies)/len(latencies):.2f} ms")
