#!/usr/bin/env python3
"""
Demo script showing how to use service-specific metrics export

This demonstrates the PrometheusExporter with different service types
"""
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitor.exporter import PrometheusExporter


def demo_service_queries():
    """Demonstrate service-specific query selection"""
    print("=" * 70)
    print("Service-Specific Metrics Demo")
    print("=" * 70)
    print()
    
    # Demo different services
    services = ["vllm", "ollama", "qdrant", "prometheus", "grafana", "unknown"]
    
    for service in services:
        print(f"📊 Service: {service}")
        print("-" * 70)
        
        # Create exporter instance with service name
        exporter = PrometheusExporter(
            prometheus_url="http://example:9090",
            service_name=service
        )
        
        # Get queries for this service
        queries = exporter.get_queries_for_service()
        
        print(f"Total metrics: {len(queries)}")
        print()
        
        # Show common metrics
        common_count = len([k for k in queries if k in exporter.COMMON_QUERIES])
        print(f"  Common metrics: {common_count}")
        for metric in sorted(exporter.COMMON_QUERIES.keys()):
            print(f"    - {metric}")
        
        # Show service-specific metrics
        service_specific = [k for k in queries if k not in exporter.COMMON_QUERIES]
        if service_specific:
            print(f"\n  Service-specific metrics: {len(service_specific)}")
            for metric in sorted(service_specific):
                print(f"    - {metric}")
        else:
            print(f"\n  Service-specific metrics: 0 (using common only)")
        
        print()
        print()


def demo_export_usage():
    """Show how to export metrics"""
    print("=" * 70)
    print("Export Usage Examples")
    print("=" * 70)
    print()
    
    print("Example 1: Export vLLM metrics (instant snapshot)")
    print("-" * 70)
    print("""
from src.monitor.exporter import PrometheusExporter
from pathlib import Path

# Create exporter for vLLM service
exporter = PrometheusExporter(
    prometheus_url="http://node01:9090",
    service_name="vllm"
)

# Export instant metrics (automatically uses vLLM-specific metrics)
exporter.export_instant_metrics(
    output_path=Path("metrics/vllm_snapshot.json"),
    format="json"
)

# Or export to CSV
exporter.export_instant_metrics(
    output_path=Path("metrics/vllm_snapshot.csv"),
    format="csv"
)
""")
    
    print("\nExample 2: Export time-series data")
    print("-" * 70)
    print("""
# Export last hour of metrics
exporter.export_range_metrics(
    output_path=Path("metrics/vllm_timeseries.json"),
    format="json",
    start=None,  # defaults to 1 hour ago
    end=None,    # defaults to now
    step="15s"
)
""")
    
    print("\nExample 3: Using custom queries")
    print("-" * 70)
    print("""
# Override with custom queries
custom_queries = {
    "vllm_requests_total": "Total requests",
    "vllm_gpu_cache_usage_perc": "GPU cache usage",
}

exporter.export_instant_metrics(
    output_path=Path("metrics/custom.json"),
    queries=custom_queries,
    format="json"
)
""")
    
    print("\nExample 4: Via MonitorManager")
    print("-" * 70)
    print("""
from src.monitor.manager import MonitorManager

manager = MonitorManager()

# Export metrics for a running monitor
# Service name is automatically determined from recipe
manager.export_prometheus_metrics(
    monitor_id="your-monitor-id",
    export_type="instant",
    format="json"
)

# Export time-series data
manager.export_prometheus_metrics(
    monitor_id="your-monitor-id",
    export_type="range",
    format="csv",
    start="2025-12-02T10:00:00Z",
    end="2025-12-02T11:00:00Z",
    step="30s"
)
""")


if __name__ == "__main__":
    demo_service_queries()
    demo_export_usage()
