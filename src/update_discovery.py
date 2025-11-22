#!/usr/bin/env python3
"""Utility to manually update discovery info from a running SLURM job"""

import sys
import subprocess
from .discover import write_discover_info, read_discover_info

def get_job_info(job_id: str):
    """Get node and status from SLURM job"""
    try:
        result = subprocess.run(
            ["squeue", "-j", job_id, "--format=%T,%N", "--noheader"],
            check=True,
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        if output:
            parts = output.split(",")
            status = parts[0]
            node = parts[1] if len(parts) > 1 else None
            return status, node
    except subprocess.CalledProcessError:
        return None, None
    return None, None

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.update_discovery <service_name> [job_id]")
        print("\nExample: python -m src.update_discovery vllm 3757031")
        sys.exit(1)
    
    service_name = sys.argv[1]
    
    # Try to read existing discovery info
    try:
        info = read_discover_info(service_name)
        job_id = sys.argv[2] if len(sys.argv) > 2 else info.get("job_id")
        
        if not job_id:
            print(f"Error: No job_id found. Provide it as: python -m src.update_discovery {service_name} <job_id>")
            sys.exit(1)
        
        print(f"Updating discovery for service '{service_name}' from job {job_id}...")
        
        status, node = get_job_info(job_id)
        
        if not node:
            print(f"Error: Could not get node info for job {job_id}. Job may not be running.")
            sys.exit(1)
        
        # Update discovery info
        info["node"] = node
        if "ports" not in info or not info["ports"]:
            print("Warning: No ports in discovery info. Using default [8000]")
            info["ports"] = [8000]
        
        write_discover_info(service_name, info)
        
        print(f"✓ Updated discovery info:")
        print(f"  Service: {service_name}")
        print(f"  Job ID: {job_id}")
        print(f"  Node: {node}")
        print(f"  Ports: {info['ports']}")
        print(f"  Status: {status}")
        
    except FileNotFoundError:
        print(f"Error: No discovery file found for service '{service_name}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
