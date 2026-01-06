# AI-Factories Framework

A unified framework for deploying, monitoring, and benchmarking AI services on HPC clusters with SLURM.

## Overview

AI-Factories provides three integrated modules:

- **Server**: Deploy AI services (vLLM, Ollama) as SLURM jobs
- **Monitor**: Deploy Prometheus monitoring for services
- **Client**: Run benchmarks against deployed services

All operations are orchestrated through SLURM, deploying containerized services via Apptainer.

## Getting Started on MeluXina

### Prerequisites

- Access to MeluXina cluster
- SLURM account configured (e.g., p200981)

### Setup Steps

1. **Access MeluXina**

   ```bash
   ssh <user>@meluxina.lxp.lu
   ```

2. **Request interactive session**

   ```bash
   salloc -A p200981 -t 02:00:00 -q dev
   ```

3. **Run setup script**

   ```bash
   cd /path/to/repo/
   ./setup.sh
   ```

4. **Configure environment**
   ```bash
   export SLURM_ACCOUNT=p200981  # or your account
   ```

### Basic Usage

All commands use the Python module interface. Thanks to automatic service discovery, you no longer need to manually track job IDs or endpoints!

```bash
# Deploy a server (automatically registers its endpoint)
python -m src.server run --recipe vllm-server

# Start monitoring (automatically finds the server)
python -m src.monitor start --recipe vllm-monitor
# Output: Prometheus URL: http://node-01:9090

# Run benchmark (automatically finds the server)
python -m src.client run --recipe vllm-simple-test

# List discovered services
python -m src.list_services

# Cleanup
python -m src.monitor stop-all
python -m src.server stop-all
python -m src.clear_services  # Clear discovery cache
```

## Architecture

### Service Discovery

The framework includes automatic service discovery that eliminates manual endpoint management.

**How it works:**

- When a server starts, it automatically registers its connection details (node, port, job ID) in `~/.aibenchmark/discover/`
- All recipes now include a `service_name` field (e.g., `vllm`) that links server, client, and monitor
- Clients and monitors automatically find servers by looking up the `service_name`
- No more copying job IDs or endpoints between commands!

**Recipe Configuration:**

```yaml
name: vllm-server
service_name: vllm # This is the discovery key
description: vLLM inference server
```

**Utility Commands:**

```bash
python -m src.list_services      # Show all discovered services
python -m src.clear_services     # Clear discovery cache
python -m src.update_discovery vllm <job-id>  # Manually update (rarely needed)
```

### Directory Structure

```
/
 setup.sh                  # Setup script for MeluXina
 cli.py                    # Python CLI router
 config/
   └── slurm.yml            # SLURM configuration
 recipes/
   ├── servers/             # Server deployment recipes
   ├── clients/             # Client benchmark recipes
   └── monitors/            # Monitor stack recipes
       ├── vllm-monitor.yml
       └── ollama-monitor.yml
 src/
   ├── server/              # Server deployment module
   ├── client/              # Client benchmark module
 monitor/             # Monitoring module   └
       ├── manager.py       # Orchestration logic
       ├── orchestrator.py  # SLURM job management
       ├── models.py        # Data models
 recipe_loader.py       └─
 logs/
    ├── servers/
 clients/
    └── monitors/            # Monitor state and logs
        ├── instances.json   # Persistent state
        └── slurm/           # SLURM job logs
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
- **Metrics Export**: Export Prometheus data to JSON/CSV with service-specific metrics

Key components:

- `MonitorManager`: Orchestrates monitor lifecycle
- `MonitorOrchestrator`: SLURM job submission and management
- `MonitorRecipeLoader`: YAML recipe parsing
- Models: `MonitorRecipe`, `MonitorInstance`, `PrometheusConfig`, `TargetService`

#### Client Module

Executes benchmarks against deployed services:

- Supports various workload patterns
- Collects performance metrics
- Generates reports

## Workflows

### Deploy and Monitor a vLLM Server

With automatic service discovery, the workflow is now streamlined:

```bash
# Start interactive session
salloc -A p200981 -t 02:00:00 -q dev

# Run setup
./setup.sh
export SLURM_ACCOUNT=p200981

# Deploy server (automatically registers as 'vllm')
python -m src.server run --recipe vllm-server
# → Submitted 1 instance(s)
# → vllm-server:01b9e92d -> 3757043

# Verify service is discovered
python -m src.list_services
# → Service: vllm
# →   node: mel2013, ports: [8000]

# Start monitoring (automatically finds 'vllm' service)
python -m src.monitor start --recipe vllm-monitor
# → Monitor ID: abc12345-...
# → Prometheus: http://node-01:9090

# Access Prometheus (from your local machine, open new terminal)
ssh -L 9090:node-01:9090 <user>@meluxina.lxp.lu
# → Browser: http://localhost:9090

# Run benchmark (automatically finds 'vllm' service)
python -m src.client run --recipe vllm-simple-test
# → Benchmark results...

# View metrics in Prometheus
# → Targets: http://localhost:9090/targets
# → Graphs: http://localhost:9090/graph

# Export metrics to JSON/CSV for analysis
python -m src.monitor export --id abc12345 --format json --type instant
# → Metrics saved to logs/monitors/abc12345.../metrics/

python -m src.monitor export --id abc12345 --format csv --type range
# → Time-series data exported to CSV

# Cleanup
python -m src.monitor stop-all
python -m src.server stop-all
python -m src.clear_services
```

### Monitor Existing SLURM Job

You can still monitor a job by its ID if needed.

```bash
# Check running jobs
squeue -u $USER
# → Job ID: 67890

# Start monitoring
python -m  monitor start --recipe vllm-monitor --targets 67890
```

### List All Resources

```bash
# See all available recipes
python -m  server list
python -m  monitor list
python -m  client list

# See running instances
python -m  server status
python -m  monitor list

# Check SLURM jobs
squeue -u $USER
```

## Dependencies

- Python 3.12+
- loguru >= 0.7.0
- pyyaml >= 6.0
- python-dotenv >= 0.19.0
- requests >= 2.28.0

Install on MeluXina:

```bash
./setup.sh  # On MeluXina with interactive session
```

## License

See LICENSE file.
