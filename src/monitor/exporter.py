"""
Prometheus Metrics Exporter

Exports Prometheus metrics to human-readable formats (JSON/CSV)
"""
from __future__ import annotations

import csv
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal

from loguru import logger


class PrometheusExporter:
    """Export Prometheus metrics to JSON/CSV formats"""

    # Common system and HTTP metrics (always included)
    COMMON_QUERIES = {
        # System metrics
        "process_cpu_seconds_total": "Total CPU time",
        "process_resident_memory_bytes": "Resident memory in bytes",
        "process_virtual_memory_bytes": "Virtual memory in bytes",
        
        # HTTP metrics
        "http_request_duration_seconds": "HTTP request duration",
        "http_requests_total": "Total HTTP requests",
    }
    
    # Service-specific metrics registry
    SERVICE_METRICS = {
        "vllm": {
            "vllm_requests_total": "Total number of requests",
            "vllm_request_duration_seconds": "Request duration in seconds",
            "vllm_time_to_first_token_seconds": "Time to first token in seconds",
            "vllm_time_per_output_token_seconds": "Time per output token in seconds",
            "vllm_num_requests_running": "Number of running requests",
            "vllm_num_requests_waiting": "Number of waiting requests",
            "vllm_gpu_cache_usage_perc": "GPU cache usage percentage",
            "vllm_cpu_cache_usage_perc": "CPU cache usage percentage",
        },
        "prometheus": {
            "prometheus_tsdb_head_series": "Total number of series in the head block",
            "prometheus_tsdb_head_samples_appended_total": "Total number of samples appended",
            "prometheus_http_requests_total": "Total HTTP requests",
        },
    }

    def __init__(self, prometheus_url: str, service_name: Optional[str] = None):
        """
        Initialize exporter
        
        Args:
            prometheus_url: Base URL of Prometheus instance (e.g., http://node:9090)
            service_name: Name of the service being monitored (e.g., 'vllm', 'ollama')
                         Used to select appropriate metrics
        """
        self.prometheus_url = prometheus_url.rstrip("/")
        self.api_url = f"{self.prometheus_url}/api/v1"
        self.service_name = service_name
        
    def get_queries_for_service(self, service_name: Optional[str] = None) -> Dict[str, str]:
        """
        Get appropriate metric queries for a service
        
        Args:
            service_name: Service name (uses instance service_name if not provided)
            
        Returns:
            Dict of {metric_name: description} including common + service-specific metrics
        """
        service = service_name or self.service_name
        
        # Start with common metrics
        queries = dict(self.COMMON_QUERIES)
        
        # Add service-specific metrics if available
        if service and service in self.SERVICE_METRICS:
            queries.update(self.SERVICE_METRICS[service])
            logger.info(f"Using {len(self.SERVICE_METRICS[service])} service-specific metrics for '{service}'")
        elif service:
            logger.warning(f"No specific metrics defined for service '{service}', using only common metrics")
        
        return queries
        
    def test_connection(self) -> bool:
        """Test connection to Prometheus"""
        try:
            response = requests.get(f"{self.api_url}/query", params={"query": "up"}, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to connect to Prometheus: {e}")
            return False

    def query_instant(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Execute instant query on Prometheus
        
        Args:
            query: PromQL query string
            
        Returns:
            Query result or None if failed
        """
        try:
            response = requests.get(
                f"{self.api_url}/query",
                params={"query": query},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                return data.get("data", {})
            else:
                logger.warning(f"Query failed: {query} - {data.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return None

    def query_range(
        self,
        query: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        step: str = "15s"
    ) -> Optional[Dict[str, Any]]:
        """
        Execute range query on Prometheus
        
        Args:
            query: PromQL query string
            start: Start time (RFC3339 or Unix timestamp). Defaults to 1 hour ago
            end: End time (RFC3339 or Unix timestamp). Defaults to now
            step: Query resolution step
            
        Returns:
            Query result or None if failed
        """
        try:
            # Default to last hour if not specified
            if not end:
                end = datetime.utcnow().isoformat() + "Z"
            if not start:
                # 1 hour ago
                from datetime import timedelta
                start_time = datetime.utcnow() - timedelta(hours=1)
                start = start_time.isoformat() + "Z"
            
            response = requests.get(
                f"{self.api_url}/query_range",
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "step": step
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                return data.get("data", {})
            else:
                logger.warning(f"Range query failed: {query} - {data.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying Prometheus range: {e}")
            return None

    def get_all_metrics(self) -> List[str]:
        """Get list of all available metrics from Prometheus"""
        try:
            response = requests.get(f"{self.api_url}/label/__name__/values", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching metric names: {e}")
            return []

    def export_instant_metrics(
        self,
        output_path: Path,
        queries: Optional[Dict[str, str]] = None,
        format: Literal["json", "csv"] = "json"
    ) -> bool:
        """
        Export instant metric values to file
        
        Args:
            output_path: Path to output file
            queries: Dict of {metric_name: description}. 
                    If None, uses service-specific queries based on service_name
            format: Output format (json or csv)
            
        Returns:
            True if export succeeded
        """
        # Use service-specific queries if none provided
        if queries is None:
            queries = self.get_queries_for_service()
        
        logger.info(f"Exporting {len(queries)} metrics to {output_path}")
        
        results = {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "prometheus_url": self.prometheus_url,
            "metrics": {}
        }
        
        # Query each metric
        for metric_name, description in queries.items():
            logger.debug(f"Querying: {metric_name}")
            data = self.query_instant(metric_name)
            
            if data and data.get("result"):
                results["metrics"][metric_name] = {
                    "description": description,
                    "result_type": data.get("resultType"),
                    "values": data.get("result")
                }
            else:
                results["metrics"][metric_name] = {
                    "description": description,
                    "error": "No data available"
                }
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            logger.info(f"✓ Exported metrics to {output_path}")
            return True
        elif format == "csv":
            return self._write_instant_csv(results, output_path)
        
        return False

    def export_range_metrics(
        self,
        output_path: Path,
        queries: Optional[Dict[str, str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        step: str = "15s",
        format: Literal["json", "csv"] = "json"
    ) -> bool:
        """
        Export time-series metric data to file
        
        Args:
            output_path: Path to output file
            queries: Dict of {metric_name: description}. 
                    If None, uses service-specific queries based on service_name
            start: Start time (defaults to 1 hour ago)
            end: End time (defaults to now)
            step: Query resolution step
            format: Output format (json or csv)
            
        Returns:
            True if export succeeded
        """
        # Use service-specific queries if none provided
        if queries is None:
            queries = self.get_queries_for_service()
        
        logger.info(f"Exporting time-series data for {len(queries)} metrics to {output_path}")
        
        results = {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "prometheus_url": self.prometheus_url,
            "time_range": {
                "start": start or "1 hour ago",
                "end": end or "now",
                "step": step
            },
            "metrics": {}
        }
        
        # Query each metric
        for metric_name, description in queries.items():
            logger.debug(f"Querying range: {metric_name}")
            data = self.query_range(metric_name, start=start, end=end, step=step)
            
            if data and data.get("result"):
                results["metrics"][metric_name] = {
                    "description": description,
                    "result_type": data.get("resultType"),
                    "values": data.get("result")
                }
            else:
                results["metrics"][metric_name] = {
                    "description": description,
                    "error": "No data available"
                }
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            logger.info(f"✓ Exported time-series metrics to {output_path}")
            return True
        elif format == "csv":
            return self._write_range_csv(results, output_path)
        
        return False

    def _write_instant_csv(self, results: Dict, output_path: Path) -> bool:
        """Write instant metrics to CSV format"""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow(["Exported At", results["exported_at"]])
                writer.writerow(["Prometheus URL", results["prometheus_url"]])
                writer.writerow([])
                
                # Metrics header
                writer.writerow(["Metric", "Description", "Labels", "Value", "Timestamp"])
                
                # Data rows
                for metric_name, metric_data in results["metrics"].items():
                    if "error" in metric_data:
                        writer.writerow([metric_name, metric_data["description"], "", "ERROR", ""])
                        continue
                    
                    for item in metric_data.get("values", []):
                        labels = json.dumps(item.get("metric", {}))
                        value = item.get("value", ["", ""])[1]  # [timestamp, value]
                        timestamp = item.get("value", ["", ""])[0]
                        
                        writer.writerow([
                            metric_name,
                            metric_data["description"],
                            labels,
                            value,
                            datetime.fromtimestamp(float(timestamp)).isoformat() if timestamp else ""
                        ])
            
            logger.info(f"✓ Exported instant metrics to CSV: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")
            return False

    def _write_range_csv(self, results: Dict, output_path: Path) -> bool:
        """Write range metrics to CSV format"""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow(["Exported At", results["exported_at"]])
                writer.writerow(["Prometheus URL", results["prometheus_url"]])
                writer.writerow(["Time Range", f"{results['time_range']['start']} to {results['time_range']['end']}"])
                writer.writerow(["Step", results["time_range"]["step"]])
                writer.writerow([])
                
                # Metrics header
                writer.writerow(["Metric", "Description", "Labels", "Timestamp", "Value"])
                
                # Data rows
                for metric_name, metric_data in results["metrics"].items():
                    if "error" in metric_data:
                        writer.writerow([metric_name, metric_data["description"], "", "", "ERROR"])
                        continue
                    
                    for series in metric_data.get("values", []):
                        labels = json.dumps(series.get("metric", {}))
                        
                        for timestamp, value in series.get("values", []):
                            writer.writerow([
                                metric_name,
                                metric_data["description"],
                                labels,
                                datetime.fromtimestamp(float(timestamp)).isoformat(),
                                value
                            ])
            
            logger.info(f"✓ Exported range metrics to CSV: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")
            return False

    def export_all_available_metrics(
        self,
        output_path: Path,
        format: Literal["json", "csv"] = "json"
    ) -> bool:
        """
        Export all currently available metrics
        
        Args:
            output_path: Path to output file
            format: Output format (json or csv)
            
        Returns:
            True if export succeeded
        """
        logger.info("Fetching all available metrics...")
        all_metrics = self.get_all_metrics()
        
        if not all_metrics:
            logger.warning("No metrics found")
            return False
        
        logger.info(f"Found {len(all_metrics)} metrics")
        
        # Create queries dict
        queries = {metric: f"Auto-discovered metric: {metric}" for metric in all_metrics}
        
        # Export instant values
        return self.export_instant_metrics(output_path, queries=queries, format=format)
