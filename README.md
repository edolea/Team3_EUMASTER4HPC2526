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

All commands use the Python module interface

```bash
# Deploy a server
python -m  server run --recipe vllm-server
# The server's endpoint is automatically discovered.

# Start monitoring
python -m  monitor start --recipe vllm-monitor
# Output: Prometheus URL: http://node-01:9090

# Run benchmark
python -m  client run --recipe vllm-benchmark

# Cleanup
python -m  monitor stop-all
python -m  server stop-all
```

## Architecture

### Service Discovery

The framework now includes an automatic service discovery mechanism.

- When a server is started with `server run`, it registers its connection details (node, port, job ID) in a local discovery file (`~/.aif/discover/`).
- The `client` and `monitor` modules can then read this file to find the service they need to connect to, based on the service name specified in their recipes.
- This eliminates the need to manually look up and provide node IPs, ports, or SLURM job IDs.

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

The new workflow is much simpler thanks to service discovery.

```bash
# Start interactive session
salloc -A p200981 -t 02:00:00 -q dev

# Run setup
./setup.sh
export SLURM_ACCOUNT=p200981

# Deploy server
python -m  server run --recipe vllm-server
# → The server is deployed and its endpoint is registered.

# Start monitoring
# The monitor automatically finds the vllm-server.
python -m  monitor start --recipe vllm-monitor
# → Monitor ID: abc12345-...
# → Prometheus URL: http://node-01:9090

# Access Prometheus (from your local machine, open new terminal)
ssh -L 9090:node-01:9090 <user>@meluxina.lxp.lu
# → Browser: http://localhost:9090

# Run benchmark (back in MeluXina session)
# The client automatically finds the vllm-server.
python -m  client run --recipe vllm-benchmark

# View metrics in Prometheus
# → Targets: http://localhost:9090/targets
# → Graphs: http://localhost:9090/graph

# Cleanup
python -m  monitor stop --id abc12345
python -m  server stop-all
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
