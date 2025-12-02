#!/usr/bin/env python3
"""
Periodic Metrics Export Script

Automatically exports Prometheus metrics at regular intervals for all running monitors.
Can be run as a background process or scheduled via cron.

Usage:
    python scripts/periodic_metrics_export.py --interval 300 --format json
    python scripts/periodic_metrics_export.py --interval 600 --format csv --type range
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.monitor.manager import MonitorManager


def export_all_monitors(
    manager: MonitorManager,
    format: str = "json",
    export_type: str = "instant",
    step: str = "15s"
) -> int:
    """
    Export metrics for all running monitors
    
    Returns:
        Number of successful exports
    """
    monitors = manager.list_running_monitors()
    
    if not monitors:
        logger.info("No running monitors to export")
        return 0
    
    logger.info(f"Exporting metrics for {len(monitors)} running monitor(s)")
    
    success_count = 0
    
    for monitor in monitors:
        try:
            logger.info(f"Exporting metrics for monitor: {monitor.id[:8]}...")
            
            output_file = manager.export_prometheus_metrics(
                monitor_id=monitor.id,
                format=format,
                export_type=export_type,
                step=step
            )
            
            if output_file:
                logger.info(f"✓ Exported: {output_file}")
                success_count += 1
            else:
                logger.warning(f"✗ Failed to export metrics for {monitor.id[:8]}")
                
        except Exception as e:
            logger.error(f"Error exporting metrics for {monitor.id[:8]}: {e}")
    
    logger.info(f"Exported {success_count}/{len(monitors)} monitor(s)")
    return success_count


def main():
    parser = argparse.ArgumentParser(
        description="Periodic Prometheus metrics exporter for running monitors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export every 5 minutes (300 seconds) as JSON
  python scripts/periodic_metrics_export.py --interval 300
  
  # Export every hour as CSV with time-series data
  python scripts/periodic_metrics_export.py --interval 3600 --format csv --type range
  
  # Run once and exit
  python scripts/periodic_metrics_export.py --once
        """
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Export interval in seconds (default: 300 = 5 minutes)"
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)"
    )
    
    parser.add_argument(
        "--type",
        choices=["instant", "range", "all"],
        default="instant",
        help="Export type: instant (current), range (time-series), all (all metrics) (default: instant)"
    )
    
    parser.add_argument(
        "--step",
        default="15s",
        help="Step size for range queries (default: 15s)"
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (don't loop)"
    )
    
    parser.add_argument(
        "--recipe-dir",
        default="recipes/monitors",
        help="Monitor recipe directory (default: recipes/monitors)"
    )
    
    parser.add_argument(
        "--output-root",
        default="logs/monitors",
        help="Output root directory (default: logs/monitors)"
    )
    
    args = parser.parse_args()
    
    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Add file logging
    log_dir = Path(args.output_root) / "export_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "periodic_export_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG"
    )
    
    logger.info("=" * 60)
    logger.info("Periodic Metrics Export Script")
    logger.info("=" * 60)
    logger.info(f"Interval: {args.interval}s")
    logger.info(f"Format: {args.format}")
    logger.info(f"Type: {args.type}")
    logger.info(f"Run once: {args.once}")
    logger.info("=" * 60)
    
    # Create manager
    manager = MonitorManager(
        recipe_directory=args.recipe_dir,
        output_root=args.output_root
    )
    
    if args.once:
        # Run once and exit
        export_all_monitors(
            manager,
            format=args.format,
            export_type=args.type,
            step=args.step
        )
        logger.info("Single export completed")
        return
    
    # Periodic export loop
    logger.info("Starting periodic export loop. Press Ctrl+C to stop.")
    
    try:
        while True:
            start_time = time.time()
            
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Export cycle started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'=' * 60}")
            
            export_all_monitors(
                manager,
                format=args.format,
                export_type=args.type,
                step=args.step
            )
            
            elapsed = time.time() - start_time
            wait_time = max(0, args.interval - elapsed)
            
            if wait_time > 0:
                logger.info(f"\nExport completed in {elapsed:.1f}s. Waiting {wait_time:.1f}s until next cycle...")
                time.sleep(wait_time)
            else:
                logger.warning(f"Export took {elapsed:.1f}s, longer than interval {args.interval}s!")
                
    except KeyboardInterrupt:
        logger.info("\n\nReceived interrupt signal. Shutting down...")
        logger.info("✓ Periodic export stopped")


if __name__ == "__main__":
    main()
