# Student Challenge 2025-2026 (Benchmarking AI Factories on MeluXina supercomputer)

The objective of this challenge is to prepare students for the upcoming AI Factories in the European Union. These AI Factories will harness the power of next-generation HPC and AI systems to revolutionise data processing, analytics, and model deployment. Through this challenge, students will gain practical skills in AI benchmarking, system monitoring, and real-world deployment scenarios—equipping them to design and operate future AI Factory workflows at scale.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file  with your SLURM account details
# Check out .env.example for info
nano .env

# 3. Start benchmark (example)
python -m server run --recipe example-server
python -m client run --recipe chroma-client
python -m monitor run --output results/chroma.json

```

### Server CLI quick tour

With the newly implemented server module you can explore the available recipes
and deploy them via the CLI:

```bash
# Discover recipes stored under recipes/servers
python -m server list

# Inspect metadata about a specific recipe
python -m server info --recipe example-server

# Launch one or more instances using SLURM
python -m server run --recipe example-server --count 2

# Tear down running instances
python -m server stop-all
```

## Setup

### Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```

#### Client Module

```mermaid
%% ClientModule mermaid class diagram
classDiagram
  class ClientManager {
    +recipe_loader: RecipeLoader
    +clients: Dict[str, ClientRun]
    -orchestator: ClientOrchestrator
    +add_client(name, config)
    +remove_client(name)
    +list_available_clients()
    +get_client(name)
    +run_bench(name, runs=1)
    +stop_all()
    +collect_metrics()
  }
  class RecipeLoader {
    +load_recipe(name)
    +list_available_recipes()
    +validate_recipe(recipe)
    +get_recipe_info(name)
    +create_recipe_template(name)
  }
  class ClientRecipe {
    +name
    +image
    +resources
    +endpoints
    +ports
    +validate()
  }
  class ClientInstance {
    +id
    +recipe_name
    +orchestrator_handle
    +endpoints
    +status
    +to_dict()
    +get_metrics()
    +update_status(status)
    +start()
    +stop()
  }
  class ClientOrchestrator {
    +submit(run)
    +stop(job_id)
    +status(job_id)
  }
  ClientManager --> ClientInstance
  ClientManager --> ClientRecipe
  ClientManager --> RecipeLoader
  ClientManager --> ClientOrchestrator
```

#### Server module

```mermaid
%% ServerModule mermaid class diagram
classDiagram
  class ServerManager {
    -recipe_loader: RecipeLoader
    -orchestrator: ServerOrchestrator
    +start_service(recipe_name, config)
    +stop_service(service_id)
    +list_available_services()
    +list_running_services()
    +get_service_status(service_id)
    +check_service_health(service_id)
    +get_service_logs(service_id)
    +shutdown()
  }
  class RecipeLoader {
    +load_recipe(name)
    +list_available_recipes()
    +validate_recipe(recipe)
    +get_recipe_info(name)
    +create_recipe_template(name)
  }
  class ServiceRecipe {
    +name
    +image
    +resources
    +endpoints
    +ports
    +validate()
  }
  class ServerInstance {
    +id
    -recipe
    +orchestrator_handle
    +status
    +endpoints
    +to_dict()
    +get_metrics()
    +restart()
    +update_status(status)
    +is_healthy()
  }
  class ServerOrchestrator {
    +deploy_service(recipe)
    +stop_service(handle)
    +get_service_status(handle)
    +get_service_logs(handle)
  }
  ServerManager --> ServerInstance
  ServerManager --> ServiceRecipe
  ServerManager --> RecipeLoader
  ServerManager --> ServerOrchestrator
```

#### Monitor module

```mermaid
%% MonitorModule mermaid class diagram
classDiagram
  class MonitorManager {
    +recipe_loader: RecipeLoader
    +output_root
    +_instances
    +list_available_recipes()
    +list_running_monitors()
    +start_monitor(recipe_name, targets, metadata, mode)
    +stop_monitor(monitor_id)
    +export_metrics(monitor_id, output)
    +deploy_prometheus(instance)
    +shutdown()
  }
  class RecipeLoader {
    +load_recipe(name)
    +list_available_recipes()
    +validate_recipe(recipe)
    +get_recipe_info(name)
    +create_recipe_template(name)
  }
  class MonitorRecipe {
    +name
    +collection_interval_seconds
    +prometheus_config
    +validate()
  }
  class MonitorInstance {
    +id
    +recipe
    +status
    +targets
    +metadata
    +to_dict()
    +is_healthy()
  }
  class PrometheusClient {
    +deploy(targets, config)
    +stop(instance)
    +query(instance, query)
    +start(prometheus_bin, config_path)
    +stop()
    +url
  }
  MonitorManager --> MonitorInstance
  MonitorManager --> MonitorRecipe
  MonitorManager --> RecipeLoader
  MonitorManager --> PrometheusClient
```

## Team 3 — EUMASTER4HPC2526

- Edoardo Leali
- Emanuele Caruso
- Tommaso Crippa
