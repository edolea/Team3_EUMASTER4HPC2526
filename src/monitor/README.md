# Monitor Module

Production-ready monitoring module with full SLURM integration for AI service monitoring.

## Features

- **SLURM Integration**: Deploy Prometheus as SLURM jobs using Apptainer containers
- **Automatic Target Discovery**: Resolve service endpoints from SLURM job IDs
- **Recipe-Based Configuration**: YAML recipes for monitoring stacks
- **CLI Integration**: Standalone and unified CLI support
- **State Persistence**: Track monitor instances across sessions
- **Component Management**: Lifecycle management for Prometheus instances

## Architecture

- `MonitorManager`: Orchestration and lifecycle for monitoring stacks
- `MonitorOrchestrator`: SLURM job submission and management
- `MonitorRecipeLoader`: Loads recipes from YAML files
- `MonitorRecipe` / `MonitorInstance` / `MonitorStatus`: Data models
- `PrometheusConfig` / `TargetService`: Configuration models

## Quick Start

### Standalone Usage

```python
from src.monitor import MonitorManager

# Initialize manager
mgr = MonitorManager(recipe_directory="recipes/monitors")

# List available recipes
print("Recipes:", mgr.list_available_recipes())

# Start monitoring with job ID
inst = mgr.start_monitor("vllm-monitor", target_job_ids=["12345"])
print("Started:", inst.id, inst.prometheus_url)

# Export metrics snapshot
mgr.export_metrics(inst.id, "out/snapshot.json")

# Stop monitor
mgr.stop_monitor(inst.id)
```

### CLI Usage

```bash
# Standalone monitor module
python -m src.monitor start --recipe vllm-monitor --targets 12345
python -m src.monitor list
python -m src.monitor status --id <monitor-id>
python -m src.monitor stop --id <monitor-id>

# Unified CLI
python -m our monitor start --recipe vllm-monitor --targets 12345
python -m our monitor list
python -m our monitor status --id <monitor-id>
```

## Recipe Format

Recipes are stored in `recipes/monitors/` as YAML files:

```yaml
name: vllm-monitor
description: Prometheus monitoring for vLLM service

targets:
  - name: vllm-llm
    port: 8000
    metrics_path: /metrics

prometheus:
  enabled: true
  image: docker://prom/prometheus:latest
  scrape_interval: 15s
  retention_time: 24h
  port: 9090
  partition: cpu
  resources:
    cpu_cores: 2
    memory_gb: 4
    gpu_count: 0
```

## Integration with Server Module

The monitor module can automatically discover and monitor servers deployed via the server module:

1. Deploy a server: `python -m our server run --recipe vllm-server`
2. Note the SLURM job ID from output
3. Start monitoring: `python -m our monitor start --recipe vllm-monitor --targets <job-id>`

The monitor will:
- Wait for the server job to be RUNNING
- Resolve the compute node hostname
- Configure Prometheus to scrape metrics from the server
- Deploy Prometheus as a SLURM job
- Provide a URL to access Prometheus web UI

## Directory Structure

```
our/
├── recipes/
│   └── monitors/          # Monitor recipe YAML files
│       ├── vllm-monitor.yml
│       └── ollama-monitor.yml
├── src/
│   └── monitor/
│       ├── __init__.py
│       ├── __main__.py    # CLI entry point
│       ├── manager.py     # MonitorManager
│       ├── orchestrator.py # SLURM orchestration
│       ├── recipe_loader.py
│       ├── models.py      # Data models
│       └── README.md
├── config/
│   └── slurm.yml         # SLURM configuration
└── logs/
    └── monitors/         # Monitor logs and state
```

## Configuration

SLURM settings are loaded from `config/slurm.yml` or environment variables:

- `SLURM_ACCOUNT`: SLURM account (required)
- `SLURM_PARTITION`: Partition (default: cpu)
- `SLURM_QOS`: QoS (default: default)
- `SLURM_TIME_LIMIT`: Time limit (default: 02:00:00)

## Comparison to Reference

This implementation matches the reference's production capabilities:

✅ Full SLURM orchestration with Apptainer  
✅ Automatic job node resolution  
✅ CLI integration (standalone + unified)  
✅ Component lifecycle management  
✅ State persistence  
✅ Recipe-based configuration  
✅ Target service discovery  

Differences:
- Grafana support omitted (can be added later)
- Simplified dashboard provisioning
- Streamlined for core monitoring use case
