from locust import HttpUser, task, between
import time
import json
from threading import Lock
import csv
import os

# --- Added for concurrent request tracking ---
concurrent_requests = 0
concurrent_lock = Lock()
# ---------------------------------------------

# --- Added for CSV logging ---
csv_file = time.strftime("data/%Y-%m-%d_%H-%M-%S_metrics.csv")
csv_lock = Lock()
if not os.path.exists(csv_file):
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "ttft", "total_latency", "tokens_per_request", "tps", "tpot", "concurrent_requests", "status"])
# ---------------------------------------------

class ChatCompletionsUser(HttpUser):
    wait_time = between(0, 0)
    @task
    def chat_completions(self):
        total_latency = 0
        ttft = None
        tokens_per_request = 0
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [{"role": "user", "content": "Give some concise response"}],
            "stream": True
        }

        # --- Increment concurrent requests ---
        global concurrent_requests
        with concurrent_lock:
            concurrent_requests += 1
            #print(f"[+] Concurrent Requests: {concurrent_requests}")
        # -------------------------------------

        start_time = time.perf_counter() 

        try:
            response = self.client.post("/v1/chat/completions", json=payload, headers=headers, stream=True)
            if response.status_code != 200 or response.content is None:
                print(f"Request failed with status code {response.status_code}: {response.text}")
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                with csv_lock:
                    with open(csv_file, mode="a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([timestamp, "N/A", "N/A", 0, "N/A", "N/A", concurrent_requests, "fail"])
                return
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8").strip()
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[len("data: "):].strip()
                        if data_str == "[DONE]":
                            total_latency = time.perf_counter() - start_time
                            tpot = total_latency / tokens_per_request
                            tps = tokens_per_request / total_latency
                            print(f"Total Latency: {total_latency:.3f} seconds")
                            # print(f"Time to First Token: {ttft:.3f} seconds")
                            # print(f"Tokens per Second: {tps:.3f}")
                            # print(f"Time per output token: {tpot:.3f}")

                            # --- Log metrics to CSV ---
                            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                            with csv_lock:
                                with open(csv_file, mode="a", newline="") as f:
                                    writer = csv.writer(f)
                                    writer.writerow([timestamp, f"{ttft:.4f}" if ttft is not None else "N/A", f"{total_latency:.4f}", tokens_per_request, f"{tps:.4f}", f"{tpot:.4f}", concurrent_requests, "success"])
                            # ----------------------------
                            break
                        try:
                            chunk = json.loads(data_str)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            print(content)
                            if ttft is None:
                                ttft = time.perf_counter() - start_time
                                print(f"Time to First Token: {ttft:.3f} seconds")
                            if content:
                                tokens_per_request += len(content.split())
                        except json.JSONDecodeError:
                            print("Warning: Could not decode JSON chunk")
                            pass
        finally:
            # --- Decrement concurrent requests ---
            with concurrent_lock:
                concurrent_requests -= 1
                #print(f"[-] Concurrent Requests: {concurrent_requests}")
            # --------------------------------------
