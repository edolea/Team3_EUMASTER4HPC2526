"""
This module provides a simple mechanism for service discovery by writing
and reading connection information to a file.
"""

import json
import os
from typing import Dict, Any

DISCOVERY_DIR = os.path.expanduser("~/.ubenchai/discover")


def get_discover_path(service_name: str) -> str:
    """Get the path to the discovery file for a service."""
    return os.path.join(DISCOVERY_DIR, f"{service_name}.json")


def write_discover_info(service_name: str, data: Dict[str, Any]):
    """Write discovery information to a file."""
    if not os.path.exists(DISCOVERY_DIR):
        os.makedirs(DISCOVERY_DIR)
    file_path = get_discover_path(service_name)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def read_discover_info(service_name: str) -> Dict[str, Any]:
    """Read discovery information from a file."""
    file_path = get_discover_path(service_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Discovery file not found for service: {service_name}")
    with open(file_path, "r") as f:
        return json.load(f)


def clear_discover_info(service_name: str):
    """Clear (delete) the discovery file for a service."""
    file_path = get_discover_path(service_name)
    if os.path.exists(file_path):
        os.remove(file_path)


def list_discovered_services() -> list[str]:
    """List all services with discovery info."""
    if not os.path.exists(DISCOVERY_DIR):
        return []
    
    services = []
    for filename in os.listdir(DISCOVERY_DIR):
        if filename.endswith('.json'):
            services.append(filename[:-5])  # Remove .json extension
    return sorted(services)
