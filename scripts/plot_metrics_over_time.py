#!/usr/bin/env python3
"""
Plot metrics over time from Prometheus monitoring data.
This script reads CSV exports from Prometheus and creates time-series visualizations.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import json
import sys

def load_monitoring_data(csv_path):
    """Load and parse Prometheus monitoring CSV export."""
    # Read CSV, skipping the metadata header lines
    df = pd.read_csv(csv_path, skiprows=4)
    
    # Convert timestamp to datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    return df

def plot_metric_over_time(df, metric_name, title=None, ylabel=None, output_path=None):
    """Plot a single metric over time."""
    # Filter for specific metric
    metric_df = df[df['Metric'] == metric_name].copy()
    
    if metric_df.empty:
        print(f"No data found for metric: {metric_name}")
        return
    
    # Sort by timestamp
    metric_df = metric_df.sort_values('Timestamp')
    
    # Create figure
    plt.figure(figsize=(14, 6))
    plt.plot(metric_df['Timestamp'], metric_df['Value'], marker='o', linewidth=2, markersize=4)
    
    # Formatting
    plt.title(title or f"{metric_name} over Time", fontsize=16, fontweight='bold')
    plt.xlabel('Time', fontsize=12)
    plt.ylabel(ylabel or 'Value', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Format x-axis
    plt.gcf().autofmt_xdate()
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    
    plt.tight_layout()
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved plot to {output_path}")
    else:
        plt.show()
    
    plt.close()

def plot_all_vllm_metrics(csv_path, output_dir=None):
    """Plot all vLLM-specific metrics."""
    df = load_monitoring_data(csv_path)
    
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get unique metrics
    metrics = df['Metric'].unique()
    print(f"Found {len(metrics)} unique metrics:")
    for m in metrics:
        print(f"  - {m}")
    
    # Define metrics to plot with their display names
    metric_configs = [
        ('vllm:avg_generation_throughput_toks_per_s', 
         'Average generation throughput (tokens/s)',
         'Throughput (tokens/s)'),
        ('vllm:avg_prompt_throughput_toks_per_s',
         'Average prompt throughput (tokens/s)', 
         'Throughput (tokens/s)'),
        ('vllm:gpu_cache_usage_perc',
         'GPU cache usage percentage',
         'Cache Usage (%)'),
        ('vllm:num_requests_running',
         'Number of running requests',
         'Request Count'),
        ('vllm:num_requests_waiting',
         'Number of waiting requests',
         'Request Count'),
        ('process_cpu_seconds_total',
         'Total CPU time (seconds)',
         'CPU Time (s)'),
        ('process_resident_memory_bytes',
         'Resident memory (bytes)',
         'Memory (bytes)'),
    ]
    
    for metric_name, title, ylabel in metric_configs:
        if metric_name in metrics:
            output_path = None
            if output_dir:
                safe_name = metric_name.replace(':', '_').replace('/', '_')
                output_path = output_dir / f"{safe_name}.png"
            
            plot_metric_over_time(df, metric_name, title, ylabel, output_path)
        else:
            print(f"Metric {metric_name} not found in data")

def summarize_benchmark_results(results_dir):
    """Create a summary table of all benchmark results."""
    results_dir = Path(results_dir)
    results = []
    
    # Find all result JSON files
    for json_file in sorted(results_dir.glob('*_results.json')):
        # Skip monitoring CSVs
        if 'monitoring' in json_file.name:
            continue
            
        with open(json_file) as f:
            data = json.load(f)
        
        # Extract test name
        test_name = json_file.stem.rsplit('_', 1)[0]
        
        results.append({
            'Test': test_name,
            'Total Requests': data.get('total_requests', 0),
            'Successes': data.get('successes', 0),
            'Errors': data.get('errors', 0),
            'Avg Latency (ms)': data.get('avg_latency_ms', 0),
            'Min Latency (ms)': data.get('min_latency_ms', 0),
            'Max Latency (ms)': data.get('max_latency_ms', 0),
            'Throughput (req/s)': data.get('throughput_req_per_sec', 0),
            'Duration (s)': data.get('duration_seconds', 0),
        })
    
    # Create DataFrame and print
    df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*80)
    print(df.to_string(index=False))
    print("="*80 + "\n")
    
    return df

def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_metrics_over_time.py <monitoring_csv_path> [output_dir]")
        print("   or: python plot_metrics_over_time.py --summarize <results_dir>")
        sys.exit(1)
    
    if sys.argv[1] == '--summarize':
        results_dir = sys.argv[2] if len(sys.argv) > 2 else './results'
        summarize_benchmark_results(results_dir)
    else:
        csv_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        
        print(f"Loading monitoring data from: {csv_path}")
        plot_all_vllm_metrics(csv_path, output_dir)
        print("\nDone!")

if __name__ == '__main__':
    main()
