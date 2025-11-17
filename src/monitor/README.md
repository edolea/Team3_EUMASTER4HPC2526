# monitor_module

Minimal implementation of a monitoring module following your class diagram:

- `MonitorManager`: orchestration and lifecycle for monitors
- `MonitorRecipeLoader`: loads recipes from YAML
- `MonitorRecipe` / `MonitorInstance` / `MonitorStatus`: models
- `PrometheusClient`: thin wrapper; stubs Prometheus unless given a binary

## Quickstart

```python
from monitor_module import MonitorRecipeLoader, MonitorManager

loader = MonitorRecipeLoader(recipe_directory="monitor_module/recipes")
mgr = MonitorManager(loader, output_root="out")
print("Recipes:", loader.list_available())

inst = mgr.start_monitor("cpu_metrics", targets=["localhost:9100"])
print("Started:", inst.id, inst.prometheus_url)

mgr.export_metrics(inst.id, "out/snapshot.json")
mgr.stop_monitor(inst.id)
```

If you want a real Prometheus instance, pass a valid `prometheus_bin` to `start_monitor`
(otherwise a no-op URL is returned and no process is started).
