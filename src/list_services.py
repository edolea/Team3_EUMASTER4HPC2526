#!/usr/bin/env python3
"""Debug utility to list discovered services"""

from .discover import list_discovered_services, read_discover_info
import json

def main():
    services = list_discovered_services()
    
    if not services:
        print("No discovered services found")
        return
    
    print("Discovered Services:")
    print("=" * 60)
    
    for service in services:
        try:
            info = read_discover_info(service)
            print(f"\nService: {service}")
            print(f"   {json.dumps(info, indent=6)}")
        except Exception as e:
            print(f"\n{service}: Error reading info - {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
