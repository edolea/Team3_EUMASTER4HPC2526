import time
import json
import requests
from datetime import datetime
from pathlib import Path


class WorkloadRunner:
    def __init__(self, endpoint, pattern='closed-loop', duration=60, 
                 concurrent_users=1, think_time=0, requests_per_user=100,
                 headers=None, payload=None, timeout=30):
        self.endpoint = endpoint
        self.pattern = pattern
        self.duration = duration
        self.concurrent_users = concurrent_users
        self.think_time_ms = think_time
        self.requests_per_user = requests_per_user
        self.headers = headers or {}
        self.payload = payload or {}
        self.timeout = timeout
        
        self.results = []
        self.errors = []

    def run(self):
        print(f"Starting benchmark: {self.endpoint}")
        print(f"Pattern: {self.pattern}, Duration: {self.duration}s, Users: {self.concurrent_users}")
        
        start_time = time.time()
        
        if self.pattern == 'closed-loop':
            self._run_closed_loop()
        elif self.pattern == 'open-loop':
            self._run_open_loop()
        else:
            raise ValueError(f"Unknown pattern: {self.pattern}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        return self._compute_metrics(total_duration)

    def _run_closed_loop(self):
        total_requests = self.requests_per_user * self.concurrent_users
        start_time = time.time()
        
        for i in range(total_requests):
            if time.time() - start_time >= self.duration:
                break
            
            self._make_request()
            
            if self.think_time_ms > 0:
                time.sleep(self.think_time_ms / 1000.0)

    def _run_open_loop(self):
        start_time = time.time()
        
        while time.time() - start_time < self.duration:
            self._make_request()

    def _make_request(self):
        req_start = time.time()
        
        try:
            response = requests.post(
                self.endpoint,
                json=self.payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            req_end = time.time()
            latency_ms = (req_end - req_start) * 1000
            
            self.results.append({
                'timestamp': req_start,
                'latency_ms': latency_ms,
                'status_code': response.status_code,
                'success': 200 <= response.status_code < 300
            })
        
        except Exception as e:
            req_end = time.time()
            latency_ms = (req_end - req_start) * 1000
            
            self.errors.append({
                'timestamp': req_start,
                'error': str(e),
                'latency_ms': latency_ms
            })
            
            self.results.append({
                'timestamp': req_start,
                'latency_ms': latency_ms,
                'status_code': 0,
                'success': False
            })

    def _compute_metrics(self, total_duration):
        total_requests = len(self.results)
        successes = sum(1 for r in self.results if r['success'])
        errors = len(self.errors)
        
        latencies = [r['latency_ms'] for r in self.results]
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
        else:
            avg_latency = min_latency = max_latency = 0
        
        throughput = total_requests / total_duration if total_duration > 0 else 0
        
        return {
            'total_requests': total_requests,
            'successes': successes,
            'errors': errors,
            'avg_latency_ms': round(avg_latency, 2),
            'min_latency_ms': round(min_latency, 2),
            'max_latency_ms': round(max_latency, 2),
            'throughput_req_per_sec': round(throughput, 2),
            'duration_seconds': round(total_duration, 2),
            'timestamp': datetime.now().isoformat(),
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Workload Runner')
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--pattern', default='closed-loop')
    parser.add_argument('--duration', type=int, default=60)
    parser.add_argument('--concurrent-users', type=int, default=1)
    parser.add_argument('--think-time', type=int, default=0)
    parser.add_argument('--requests-per-user', type=int, default=100)
    parser.add_argument('--payload', default='{}', help='JSON payload for requests')
    parser.add_argument('--headers', default='{}', help='JSON headers for requests')
    parser.add_argument('--output', required=True)
    
    args = parser.parse_args()
    
    # Parse JSON arguments
    payload = json.loads(args.payload) if args.payload else {}
    headers = json.loads(args.headers) if args.headers else {}
    
    runner = WorkloadRunner(
        endpoint=args.endpoint,
        pattern=args.pattern,
        duration=args.duration,
        concurrent_users=args.concurrent_users,
        think_time=args.think_time,
        requests_per_user=args.requests_per_user,
        payload=payload,
        headers=headers
    )
    
    metrics = runner.run()
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print("\n=== Benchmark Results ===")
    print(f"Total Requests: {metrics['total_requests']}")
    print(f"Successes: {metrics['successes']}")
    print(f"Errors: {metrics['errors']}")
    print(f"Avg Latency: {metrics['avg_latency_ms']} ms")
    print(f"Min Latency: {metrics['min_latency_ms']} ms")
    print(f"Max Latency: {metrics['max_latency_ms']} ms")
    print(f"Throughput: {metrics['throughput_req_per_sec']} req/s")
    print(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()
