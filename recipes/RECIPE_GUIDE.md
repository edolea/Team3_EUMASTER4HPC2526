# Recipe Creation Guide

This guide explains how to create recipes for servers, clients, and monitors in the AI-Factories framework.

## Overview

Recipes are YAML files that define how to deploy and interact with AI services. All recipes for the same service share a common `service_name` field that enables automatic discovery.

## Recipe Types

### 1. Server Recipes

Server recipes define how to deploy an AI service (e.g., vLLM, Ollama) on the HPC cluster.

**Location**: `recipes/servers/`

**Template**:

```yaml
name: my-service-server
service_name: my-service # Discovery key - must match across all recipes
description: Brief description of what this server does

service:
  # Bash command to start the service
  command: |
    #!/bin/bash
    set -e

    # Load required modules
    module load env/release/2024.1
    module load Apptainer/1.3.6-GCCcore-13.3.0

    # Your service startup commands here
    echo "Starting my service..."

    # Example: Run a container
    apptainer exec my-service.sif /start-service.sh

  working_dir: . # Working directory (relative or absolute)

  env:
    # Environment variables
    MY_VAR: "value"
    ANOTHER_VAR: "another-value"

  ports:
    - 8000 # List of ports your service uses

orchestration:
  resources:
    cpu_cores: 8
    memory_gb: 64
    gpu_count: 1 # Set to 0 if no GPU needed
    partition: gpu # or "cpu"
    time_limit: "02:00:00" # HH:MM:SS format
```

**Key Points**:

- `service_name`: This is the discovery identifier. Use the same value in client and monitor recipes.
- `command`: Multi-line bash script that starts your service
- `ports`: List all ports your service exposes (used for discovery)
- `partition`: Use `gpu` for GPU services, `cpu` for CPU-only

**Example Services**:

- vLLM (LLM inference)
- Ollama (LLM inference)
- ChromaDB (vector database)

---

### 2. Monitor Recipes

Monitor recipes define Prometheus monitoring for your services.

**Location**: `recipes/monitors/`

**Template**:

```yaml
name: my-service-monitor
service_name: my-service # Must match server's service_name
description: Monitoring stack for my-service

targets:
  - name: my-service-metrics # Human-readable target name
    port: 8000 # Port where metrics are exposed (usually same as service port)
    metrics_path: /metrics # Prometheus metrics endpoint path

prometheus:
  enabled: true
  image: docker://prom/prometheus:latest
  scrape_interval: 15s # How often to collect metrics
  retention_time: 24h # How long to keep metrics
  port: 9090 # Prometheus UI port
  partition: cpu # Usually CPU is enough for monitoring
  resources:
    cpu_cores: 2
    memory_gb: 4
    gpu_count: 0
```

**Key Points**:

- `service_name`: Must match the server recipe's `service_name`
- `targets[].name`: Logical name for the target (shows up in Prometheus)
- `targets[].port`: The port where your service exposes metrics
- `metrics_path`: Most services use `/metrics`, but some may differ (e.g., `/api/metrics`)
- Prometheus resources: 2 CPU cores and 4GB RAM is usually sufficient

**Metrics Endpoints**:

- vLLM: Port 8000, path `/metrics`
- Most Python services: Use `prometheus_client` library
- Custom services: Implement Prometheus exposition format

---

### 3. Client Recipes

Client recipes define benchmarks and load tests for your services.

**Location**: `recipes/clients/`

**Template**:

```yaml
name: my-service-benchmark
service_name: my-service # Must match server's service_name
description: Benchmark test for my-service

target:
  protocol: http # or https
  timeout_seconds: 60 # Request timeout

workload:
  pattern: closed-loop # or "open-loop"
  duration_seconds: 300 # How long to run the benchmark
  concurrent_users: 10 # Number of concurrent requests (closed-loop)
  think_time_ms: 100 # Delay between requests per user (closed-loop)
  # requests_per_second: 50  # Rate for open-loop pattern

dataset:
  type: synthetic # or "file" for custom datasets
  params:
    # Service-specific parameters
    # Example for LLM services:
    model_name: my-model
    prompt_length: 100
    max_tokens: 50
    temperature: 0.7

orchestration:
  mode: slurm
  resources:
    partition: cpu
    cpu_cores: 4
    memory_gb: 8
    time_limit: "00:30:00"

output:
  metrics:
    - latency
    - throughput
    - errors
    - success_rate
    - p50
    - p95
    - p99
  format: json
  destination: ./results
```

**Key Points**:

- `service_name`: Must match the server recipe - used for auto-discovery
- `workload.pattern`:
  - `closed-loop`: Fixed number of concurrent users, think time between requests
  - `open-loop`: Fixed request rate (requests per second)
- `dataset`: Customize based on your service's API

**Workload Patterns**:

**Closed-Loop** (simulates real users):

```yaml
workload:
  pattern: closed-loop
  concurrent_users: 20
  think_time_ms: 500 # Users wait 500ms between requests
```

**Open-Loop** (fixed rate):

```yaml
workload:
  pattern: open-loop
  requests_per_second: 100 # Constant 100 req/s
```

## Best Practices

### Naming Conventions

- **Server recipes**: `<service>-server.yaml`
- **Monitor recipes**: `<service>-monitor.yml`
- **Client recipes**: `<service>-<test-type>.yaml`
- **Service name**: Use short, lowercase, hyphen-separated names (e.g., `vllm`, `fastapi-ml`, `ollama`)

### Service Name Consistency

**Critical**: All recipes for the same service MUST use the same `service_name`:

```yaml
# Server recipe
service_name: my-service

# Monitor recipe
service_name: my-service  # ✓ Same

# Client recipe
service_name: my-service  # ✓ Same
```

If they don't match, auto-discovery won't work!

### Port Selection

- Check port availability on compute nodes
- Avoid common ports (22, 80, 443, etc.)
- Use ranges: 8000-9000 are usually safe
- Services can auto-select ports (set `PORT=0` in startup script)

### Resource Allocation

**GPU Services**:

```yaml
orchestration:
  resources:
    gpu_count: 1
    partition: gpu
    cpu_cores: 8
    memory_gb: 64 # GPUs usually need more RAM
```

**CPU Services**:

```yaml
orchestration:
  resources:
    gpu_count: 0
    partition: cpu
    cpu_cores: 4
    memory_gb: 16
```
