# AI-Factories Framework

A unified framework for deploying, monitoring, and benchmarking AI services on HPC clusters with SLURM.

## Overview

AI-Factories provides three integrated modules:

- **Server**: Deploy AI services (vLLM, Ollama) as SLURM jobs
- **Monitor**: Deploy Prometheus monitoring for services
- **Client**: Run benchmarks against deployed services

All operations are orchestrated through SLURM, deploying containerized services via Apptainer.

## Quick Start

### Installation

```bash
cd /path/to/repo
pip install -r requirements.txt
```

### Basic Workflow

```bash
# 1. Deploy a server
./ai-factories.sh server run --recipe vllm-server
# Output: Job ID: 12345

# 2. Start monitoring
./ai-factories.sh monitor start --recipe vllm-monitor --targets 12345
# Output: Prometheus URL: http://node-01:9090

# 3. Run benchmark
./ai-factories.sh client run --recipe vllm-benchmark

# 4. Cleanup
./ai-factories.sh monitor stop-all
./ai-factories.sh server stop-all
```

## Architecture

### Directory Structure

```
root/
 ai-factories.sh          # Main CLI wrapper script
 cli.py                   # Python CLI router
 config/
   └── slurm.yml           # SLURM configuration
 recipes/
   ├── servers/            # Server deployment recipes
   ├── clients/            # Client benchmark recipes
   └── monitors/           # Monitor stack recipes
       ├── vllm-monitor.yml
       └── ollama-monitor.yml
 src/
   ├── server/             # Server deployment module
   ├── client/             # Client benchmark module
   └── monitor/            # Monitoring module
       ├── manager.py      # Orchestration logic
       ├── orchestrator.py # SLURM job management
       ├── models.py       # Data models
       └── recipe_loader.py
 logs/
    ├── servers/
    ├── clients/
    └── monitors/           # Monitor state and logs
        ├── instances.json  # Persistent state
        └── slurm/          # SLURM job logs
```

### Module Overview

#### Server Module

Deploys AI services as containerized SLURM jobs:

- Manages service lifecycle (start, stop, status)
- Handles resource allocation (CPU, GPU, memory)
- Provides service endpoints for clients

#### Monitor Module

Deploys Prometheus monitoring stacks:

- **Automatic Discovery**: Resolves SLURM job IDs to compute nodes
- **SLURM Integration**: Prometheus runs as SLURM job with Apptainer
- **Recipe-Based**: YAML configs for monitoring stacks
- **Component Tracking**: Manages Prometheus lifecycle
- **State Persistence**: Tracks monitors across sessions

Key components:

- `MonitorManager`: Orchestrates monitor lifecycle
- `MonitorOrchestrator`: SLURM job submission and management
- `MonitorRecipeLoader`: YAML recipe parsing
- Models: `MonitorRecipe`, `MonitorInstance`, `PrometheusConfig`, `TargetService`

#### Client Module

Runs benchmarks against deployed services:

- Configurable workload patterns
- Metrics collection and reporting
- Results persistence

## How It Works

### 1. Server Deployment

```bash
./ai-factories.sh server run --recipe vllm-server
```

**Process:**

1. Load recipe from `recipes/servers/vllm-server.yml`
2. Generate SLURM batch script with resource requirements
3. Submit job via `sbatch`
4. Return job ID and wait for RUNNING state
5. Service available at `<node>:<port>`

### 2. Monitor Deployment

```bash
./ai-factories.sh monitor start --recipe vllm-monitor --targets 12345
```

**Process:**

1. Load recipe from `recipes/monitors/vllm-monitor.yml`
2. Wait for target job 12345 to be RUNNING
3. Query SLURM to get compute node (e.g., `gpu-node-01`)
4. Resolve target endpoint: `gpu-node-01:8000`
5. Generate Prometheus config to scrape that endpoint
6. Create SLURM batch script for Prometheus
7. Deploy Prometheus as SLURM job with Apptainer
8. Wait for Prometheus job to be RUNNING
9. Return Prometheus URL: `http://prom-node:9090`

**Target Resolution:**

```python
# Automatic from job ID
target_job_ids=["12345"]
# → Queries squeue → gpu-node-01
# → Creates target: "gpu-node-01:8000"

# Or direct endpoint
targets = [{"name": "my-service", "endpoint": "node-01:8000"}]
```

### 3. Client Benchmarking

```bash
./ai-factories.sh client run --recipe vllm-benchmark
```

**Process:**

1. Load benchmark recipe with workload pattern
2. Connect to server endpoint
3. Execute benchmark requests
4. Collect metrics (latency, throughput, etc.)
5. Save results to `results/`

### Integration Flow

```

  User runs: ./ai-factories.sh                           │

                │
                ▼

  Bash Wrapper (ai-factories.sh)                         │
  - Loads MeluXina modules                               │
  - Sets up Python environment                           │
  - Routes to: python -m <module> <command>          │

                │
                ▼

  Python CLI Router (cli.py)                             │
  - Parses module (server/client/monitor)                │
  - Routes to module handler                             │

                │
        ┌───────┴───────┬────────────┐
        ▼               ▼            ▼
   ┌──────────┐    ┌────────┐    ┌──
    │ Server │    │ Client  │   │ Monitor  │
    │ Module │    │ Module  │   │ Module   │
    └────┬───┘    └────┬────┘   └───
         │             │             │
         ▼             ▼             ▼
    ┌────────
    │    SLURM Cluster (sbatch/squeue)   │
    │    - Submit jobs                   │
    │    - Monitor status                │
    │    - lifecycle Manage
    └────────────────────────────────────┘
```

## Configuration

### SLURM Settings

**Environment variables:**

```bash
export SLURM_ACCOUNT=your-account
export SLURM_PARTITION=cpu
export SLURM_QOS=default
```

**Or edit `config/slurm.yml`:**

```yaml
slurm:
  partition: cpu
  qos: default
  time_limit: "02:00:00"
  module_env: "env/release/2024.1"
  apptainer_module: "Apptainer/1.3.6-GCCcore-13.3.0"
  image_cache: "./containers"
```

### Monitor Recipe Format

Example `recipes/monitors/vllm-monitor.yml`:

```yaml
name: vllm-monitor
description: Prometheus monitoring for vLLM service

targets:
  - name: vllm-llm
    port: 8000 # Service port
    metrics_path: /metrics

prometheus:
  enabled: true
  image: docker://prom/prometheus:latest
  scrape_interval: 15s
  retention_time: 24h
  port: 9090
  partition: cpu # SLURM partition
  resources:
    cpu_cores: 2
    memory_gb: 4
    gpu_count: 0
```

## Access Services

### Prometheus Web UI

After starting a monitor, access via SSH tunnel:

```bash
# Get Prometheus URL from monitor output
# Example: http://gpu-node-02:9090

# Create SSH tunnel
ssh -L 9090:gpu-node-02:9090 user@meluxina

# Open in browser
http://localhost:9090
```

### Server Endpoints

Servers expose their service ports on compute nodes:

```bash
# Get server node and port from deployment
# Example: gpu-node-01:8000

# Test directly (if accessible)
curl http://gpu-node-01:8000/health

# Or via tunnel
ssh -L 8000:gpu-node-01:8000 user@meluxina
curl http://localhost:8000/health
```

## Programmatic Usage

### Python API

```python
from src.monitor import MonitorManager
from src.server import ServerManager

# Deploy server
server_mgr = ServerManager()
server = server_mgr.run("vllm-server")
job_id = server[0].orchestrator_handle

# Start monitoring
monitor_mgr = MonitorManager()
monitor = monitor_mgr.start_monitor(
    recipe_name="vllm-monitor",
    target_job_ids=[job_id]
)

print(f"Server: Job {job_id}")
print(f"Prometheus: {monitor.prometheus_url}")
print(f"Targets: {monitor.targets}")

# Get status
status = monitor_mgr.get_monitor_status(monitor.id)

# Cleanup
monitor_mgr.stop_monitor(monitor.id)
server_mgr.stop_all()
```

## Troubleshooting

### Python not available on login node

Use the bash wrapper `./ai-factories.sh` which automatically loads required modules.

### Monitor fails to start

```bash
# Check SLURM account
echo $SLURM_ACCOUNT

# Verify recipe exists
ls recipes/monitors/

# Check SLURM queue
squeue -u $USER
```

### Can't resolve target job

```bash
# Verify job is running
squeue -j <job-id>

# Check job details
scontrol show job <job-id>
```

### Prometheus not accessible

```bash
# Check monitor logs
cat logs/monitors/slurm/prometheus_*.log

# Verify Prometheus job
squeue | grep prometheus

# Check instance state
cat logs/monitors/instances.json
```

## Advanced Usage

### Monitor Multiple Services

```bash
# Start separate monitors
./ai-factories.sh monitor start --recipe vllm-monitor --targets 12345
./ai-factories.sh monitor start --recipe ollama-monitor --targets 12346
```

### Direct Endpoints (No Job ID)

Edit recipe to use direct endpoint:

```yaml
targets:
  - name: my-service
    endpoint: "node-01:8000" # Hardcoded
    metrics_path: /metrics
```

### Custom Scrape Intervals

```yaml
prometheus:
  scrape_interval: 5s # More frequent
  retention_time: 48h # Longer retention
```

## Dependencies

```
requests>=2.28.0
pyyaml>=6.0
python-dotenv>=0.19.0
loguru>=0.7.0
```

Install with: `pip install -r requirements.txt`
