#!/usr/bin/env python3
"""Debug utility to clear all discovered services"""

from .discover import list_discovered_services, clear_discover_info

def main():
    services = list_discovered_services()
    
    if not services:
        print("No discovered services to clear")
        return
    
    print(f"Found {len(services)} service(s) to clear:")
    for service in services:
        print(f"  - {service}")
    
    print("\nClearing all services...")
    
    cleared = 0
    for service in services:
        try:
            clear_discover_info(service)
            print(f"  ✓ Cleared: {service}")
            cleared += 1
        except Exception as e:
            print(f"  ✗ Failed to clear {service}: {e}")
    
    print(f"\nCleared {cleared}/{len(services)} service(s)")

if __name__ == "__main__":
    main()
