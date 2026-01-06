# AI-Factories Quick Reference

## Setup on MeluXina

```bash
# 1. SSH to MeluXina
ssh <user>@meluxina.lxp.lu

# 2. Request interactive session
salloc -A p200981 -t 02:00:00 -q dev

# 3. Move to repo
cd /path/to/repo

# 4. Run setup script
./setup.sh

# 5. Set account
export SLURM_ACCOUNT=p200981
```

## Command Reference

All commands use Python module interface:

```bash
python -m src.<module> <command> [options]
```

## Service Discovery Commands

```bash
# List all discovered services
python -m src.list_services

# Clear all discovered services
python -m src.clear_services

# Manually update discovery info (rarely needed)
python -m src.update_discovery <service-name> <job-id>
# Example: python -m src.update_discovery vllm 3757043
```

## Server Commands

```bash
# Deploy server
python -m src.server run --recipe <name> [--count <n>]

# List available recipes
python -m src.server list

# Show server status
python -m src.server status

# Stop server
python -m src.server stop --name <instance>

# Stop all servers
python -m src.server stop-all

# Recipe info
python -m src.server info --recipe <name>
```

## Monitor Commands

```bash
# Start monitoring (with job ID)
python -m src.monitor start --recipe <name> --targets <job-id>[,<job-id>,...]

# Start monitoring (direct endpoint in recipe)
python -m src.monitor start --recipe <name>

# List monitors and recipes
python -m src.monitor list

# Get monitor status
python -m src.monitor status --id <monitor-id>

# Stop monitor
python -m src.monitor stop --id <monitor-id>

# Stop all monitors
python -m src.monitor stop-all

# Recipe info
python -m src.monitor info --recipe <name>

# Export Prometheus metrics
python -m src.monitor export --id <monitor-id> [--format json|csv] [--type instant|range|all]
python -m src.monitor export --id <monitor-id> --format csv --type range --start "2025-12-02T10:00:00Z" --end "2025-12-02T11:00:00Z"
```

## Client Commands

```bash
# Run benchmark
python -m src.client run --recipe <name> [--runs <n>]

# List available recipes
python -m src.client list

# Recipe info
python -m src.client info --recipe <name>
```

## Common Workflows

### Full Stack Deployment (with Auto-Discovery)

```bash
# 1. Deploy vLLM server (auto-registers as 'vllm')
python -m src.server run --recipe vllm-server
# → Submitted 1 instance(s)
# → vllm-server:01b9e92d -> 3757043

# 2. Verify discovery
python -m src.list_services
# → Service: vllm (node: mel2013, ports: [8000])

# 3. Start Prometheus monitoring (auto-finds 'vllm')
python -m src.monitor start --recipe vllm-monitor
# → Monitor ID: abc123...
# → Prometheus: http://node-01:9090

# 4. Access Prometheus (SSH tunnel from your local machine)
ssh -L 9090:node-01:9090 user@meluxina.lxp.lu
# → Browser: http://localhost:9090

# 5. Run benchmark (auto-finds 'vllm')
python -m src.client run --recipe vllm-simple-test

# 6. View metrics in Prometheus
# → http://localhost:9090/targets
# → http://localhost:9090/graph

# 7. Export metrics to JSON/CSV
python -m src.monitor export --id abc123 --format json --type instant
# → Exported to logs/monitors/abc123.../metrics/prometheus_metrics_instant_*.json

python -m src.monitor export --id abc123 --format csv --type range
# → Exported to logs/monitors/abc123.../metrics/prometheus_metrics_range_*.csv

# 8. Cleanup
python -m src.monitor stop-all
python -m src.server stop-all
python -m src.clear_services
```

### Monitor Existing Service

```bash
# If you have a running SLURM job
squeue -u $USER
# → Job ID: 67890

# Start monitoring it
python -m src.monitor start --recipe vllm-monitor --targets 67890
```

### List Everything

```bash
# See all recipes
python -m src.server list
python -m src.monitor list
python -m src.client list

# See all running instances
python -m src.server status
python -m src.monitor list  # shows running monitors

# Check SLURM jobs
squeue -u $USER
```

## Configuration Files

### SLURM Config: `config/slurm.yml`

```yaml
slurm:
  partition: cpu
  qos: default
  time_limit: "02:00:00"
  module_env: "env/release/2024.1"
  apptainer_module: "Apptainer/1.3.6-GCCcore-13.3.0"
  image_cache: "./containers"
```

### Monitor Recipe: `recipes/monitors/*.yml`

```yaml
name: my-monitor
description: Monitor my service

targets:
  - name: my-service
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

## Environment Variables

```bash
# Required
export SLURM_ACCOUNT=your-account

# Optional (override config/slurm.yml)
export SLURM_PARTITION=cpu
export SLURM_QOS=default
export SLURM_TIME_LIMIT="02:00:00"
```

## Python API

### Monitor Module

```python
from src.monitor import MonitorManager

# Initialize
mgr = MonitorManager(recipe_directory="recipes/monitors")

# List recipes
recipes = mgr.list_available_recipes()

# Start monitor with job ID
instance = mgr.start_monitor("vllm-monitor", target_job_ids=["12345"])

# Access info
print(instance.id)                # Monitor ID
print(instance.prometheus_url)    # Prometheus URL
print(instance.targets)           # Resolved targets

# Get status
status = mgr.get_monitor_status(instance.id)

# Export metrics
exported_file = mgr.export_prometheus_metrics(
    monitor_id=instance.id,
    format="json",  # or "csv"
    export_type="instant"  # or "range" or "all"
)
print(f"Metrics exported to: {exported_file}")

# Export time-series data
exported_file = mgr.export_prometheus_metrics(
    monitor_id=instance.id,
    format="csv",
    export_type="range",
    start="2025-12-02T10:00:00Z",
    end="2025-12-02T11:00:00Z",
    step="30s"
)

# Stop
mgr.stop_monitor(instance.id)
```

### Server Module

```python
from src.server import ServerManager

mgr = ServerManager()

# Deploy
instances = mgr.run("vllm-server", count=1)
job_id = instances[0].orchestrator_handle

# Status
statuses = mgr.collect_status()

# Stop
mgr.stop_all()
```

### Integration

```python
from src.server import ServerManager
from src.monitor import MonitorManager

# Deploy and monitor
server_mgr = ServerManager()
server = server_mgr.run("vllm-server")
job_id = server[0].orchestrator_handle

monitor_mgr = MonitorManager()
monitor = monitor_mgr.start_monitor("vllm-monitor", [job_id])

print(f"Server: {job_id}")
print(f"Prometheus: {monitor.prometheus_url}")
```

## File Locations

```
root/
 ai-factories.sh              # Main wrapper
 recipes/monitors/            # Monitor recipes
 logs/monitors/               # Monitor state/logs
   ├── instances.json          # Persistent state
   └── slurm/                  # SLURM job logs
 config/slurm.yml            # Configuration
```

## Metrics Export

### Export Prometheus Metrics to JSON/CSV

Export metrics from a running Prometheus instance to human-readable formats for analysis, reporting, or sharing.

```bash
# Get monitor ID
python -m src.monitor list
# → Monitor ID: abc12345-6789-...

# Export instant snapshot (current values)
python -m src.monitor export --id abc12345 --format json --type instant
# → Exported to logs/monitors/abc12345.../metrics/prometheus_metrics_instant_*.json

# Export time-series data (last hour by default)
python -m src.monitor export --id abc12345 --format csv --type range
# → Exported to logs/monitors/abc12345.../metrics/prometheus_metrics_range_*.csv

# Export specific time range
python -m src.monitor export --id abc12345 --format json --type range \
  --start "2025-12-02T10:00:00Z" --end "2025-12-02T11:00:00Z" --step "30s"

# Export all available metrics
python -m src.monitor export --id abc12345 --format json --type all
```

### Service-Specific Metrics

The exporter automatically selects appropriate metrics based on the service being monitored:

**Common metrics (always included):**

- `process_cpu_seconds_total` - Total CPU time
- `process_resident_memory_bytes` - Memory usage
- `http_requests_total` - HTTP request count

**Service-specific metrics:**

- **vLLM**: Request metrics, token generation timing, cache usage, queue depth
- **Ollama**: Request duration, model loading time
- **Qdrant**: Collections, points, search performance
- **Prometheus**: TSDB metrics, sample counts

The service type is determined from the monitor recipe's `service_name` field.

### Export Formats

**JSON format:**

```json
{
  "exported_at": "2025-12-02T15:30:00Z",
  "prometheus_url": "http://node01:9090",
  "metrics": {
    "vllm_requests_total": {
      "description": "Total number of requests",
      "result_type": "vector",
      "values": [...]
    }
  }
}
```

**CSV format:**

```csv
Metric,Description,Labels,Value,Timestamp
vllm_requests_total,Total number of requests,{...},1234,2025-12-02T15:30:00
```

### Python API

```python
from src.monitor import MonitorManager

mgr = MonitorManager()

# Export instant metrics
file_path = mgr.export_prometheus_metrics(
    monitor_id="abc12345",
    format="json",
    export_type="instant"
)

# Export time-series with custom queries
from src.monitor.exporter import PrometheusExporter

exporter = PrometheusExporter(
    prometheus_url="http://node01:9090",
    service_name="vllm"  # Auto-selects vLLM metrics
)

custom_queries = {
    "vllm_requests_total": "Total requests",
    "vllm_gpu_cache_usage_perc": "GPU cache usage"
}

exporter.export_range_metrics(
    output_path=Path("my_metrics.json"),
    queries=custom_queries,
    start="2025-12-02T10:00:00Z",
    end="2025-12-02T11:00:00Z",
    step="15s",
    format="json"
)
```

## Troubleshooting

### Check monitor state

```bash
cat logs/monitors/instances.json | python -m json.tool
```

### View Prometheus logs

```bash
ls -lt logs/monitors/slurm/prometheus_*.log | head -1 | xargs tail -50
```

### Check SLURM jobs

```bash
squeue -u $USER
squeue -j <job-id>
scontrol show job <job-id>
```

### Access Prometheus

```bash
# Get node from monitor output
# Create tunnel
ssh -L 9090:<node>:9090 user@meluxina

# Browser
http://localhost:9090
```

## Common Issues

**Problem**: "Module 'loguru' not found"  
**Solution**: `pip install -r requirements.txt`

**Problem**: "SLURM account not set"  
**Solution**: `export SLURM_ACCOUNT=your-account`

**Problem**: "Recipe not found"  
**Solution**: Check recipe exists: `ls recipes/monitors/`

**Problem**: "Can't resolve job ID"  
**Solution**: Verify job is running: `squeue -j <job-id>`

**Problem**: Python not available  
**Solution**: Request interactive session: `salloc -A p200981 -t 02:00:00 -q dev`

**Problem**: "Could not discover endpoint for service"  
**Solution**:

- Check service is running: `squeue -u $USER`
- List discovered services: `python -m src.list_services`
- If service missing node/ports, update: `python -m src.update_discovery <service> <job-id>`

**Problem**: "No valid targets found to monitor"  
**Solution**:

- Verify service exists: `python -m src.list_services`
- Check `service_name` matches in all recipes (server, client, monitor)
- Update discovery if needed: `python -m src.update_discovery <service> <job-id>`

## Tips

- Always work in an interactive session (salloc) - Python not available on login nodes
- All recipes for the same service should use the same `service_name` field
- Use `python -m src.list_services` to debug service discovery issues
- Discovery info is stored in `~/.aibenchmark/discover/`
- Monitor IDs are UUIDs - use first 8 chars for convenience
- Prometheus retains metrics based on `retention_time` in recipe
- Stop monitors when done to free SLURM resources
- Check `logs/monitors/instances.json` for persistent state
- Use SSH tunnels to access services on compute nodes
- Clear discovery cache with `python -m src.clear_services` when done
