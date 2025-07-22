from locust import HttpUser, task, between
import time
import json
from threading import Lock
import csv
import os

# --- Concurrency Tracker ---
concurrent_requests = 0
concurrent_lock = Lock()

# --- CSV Setup ---
timestamp_prefix = os.environ.get("TEST_TIMESTAMP", time.strftime("%Y-%m-%d_%H-%M-%S"))
os.makedirs("data", exist_ok=True)
csv_file = f"data/{timestamp_prefix}_metrics.csv"
csv_lock = Lock()

if not os.path.exists("data"):
    os.makedirs("data")

if not os.path.exists(csv_file):
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "ttft", "total_latency", "tokens_per_request", "tps", "tpot", "concurrent_requests", "status"])

# --- Helper to Log Metrics ---
def log_metrics(timestamp, ttft, total_latency, tokens, concurrent, status):
    tps = tokens / total_latency if total_latency > 0 else 0
    tpot = total_latency / tokens if tokens > 0 else 0
    with csv_lock:
        with open(csv_file, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, f"{ttft:.4f}" if ttft else "N/A", f"{total_latency:.4f}", tokens, 
            f"{tps:.4f}", f"{tpot:.4f}", concurrent, status
            ])

# --- Locust User Class ---
class ChatCompletionsUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {"Content-Type": "application/json"}
        # Pre-encode the payload for faster reuse
        payload = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [{"role": "user", "content": "Explain General Relativity in simple terms?"}],
            "stream": True
        }
        self.encoded_payload = json.dumps(payload)

    @task
    def chat_completions(self):
        global concurrent_requests

        # Track concurrency
        with concurrent_lock:
            concurrent_requests += 1
            current_concurrency = concurrent_requests

        ttft = None
        tokens = 0

        try:
            response = self.client.post(
                "/v1/chat/completions",
                data=self.encoded_payload,
                headers=self.headers,
                stream=True
            )
            start_time = time.perf_counter()
            
            if response.status_code != 200:
                print(f"Request failed: {response.status_code} - {response.text}")
                log_metrics(time.strftime("%Y-%m-%d %H:%M:%S"), None, 0, 0, current_concurrency, "fail")
                return
            
            for line in response.iter_lines():
                if not line:
                    continue

                decoded_line = line.decode("utf-8").strip()
                if not decoded_line.startswith("data: "):
                    continue

                data_str = decoded_line[6:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")

                    if content:
                        if ttft is None:
                            ttft = time.perf_counter() - start_time
                            print(f"Time to First Token: {ttft:.3f} sec")

                        tokens += len(content.split())
                        #print(content, end="", flush=True)

                except json.JSONDecodeError:
                    print("Warning: JSON decode failed.")

            total_latency = time.perf_counter() - start_time
            print(f"\nTotal Latency: {total_latency:.3f} sec")

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_metrics(timestamp, ttft, total_latency, tokens, current_concurrency, "success")

        finally:
            with concurrent_lock:
                concurrent_requests -= 1
