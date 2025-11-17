"""
MonitorOrchestrator - SLURM orchestration for monitoring components
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from loguru import logger

try:
    import yaml
except ImportError:
    yaml = None

from .models import PrometheusConfig, MonitorStatus


class MonitorOrchestrator:
    """
    Deploys monitoring components (Prometheus) as SLURM jobs using Apptainer
    """

    def __init__(
        self,
        partition: Optional[str] = None,
        account: Optional[str] = None,
        qos: Optional[str] = None,
        time_limit: Optional[str] = None,
        config_file: str = "config/slurm.yml",
        log_directory: str = "logs/monitors",
    ):
        """Initialize monitor orchestrator"""
        
        # Load dotenv if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Load configuration
        config = self._load_config(config_file)

        self.account = account or os.getenv("SLURM_ACCOUNT") or config.get("account")
        self.partition = (
            partition or os.getenv("SLURM_PARTITION") or config.get("partition", "cpu")
        )
        self.qos = qos or os.getenv("SLURM_QOS") or config.get("qos", "default")
        self.time_limit = (
            time_limit
            or os.getenv("SLURM_TIME_LIMIT")
            or config.get("time_limit", "02:00:00")
        )

        self.module_env = config.get("module_env", "env/release/2024.1")
        self.apptainer_module = config.get(
            "apptainer_module", "Apptainer/1.3.6-GCCcore-13.3.0"
        )
        self.image_cache_dir = config.get("image_cache", "./containers")

        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

        if not self.account:
            logger.warning("SLURM account not set. Jobs may fail to submit.")

        logger.info(
            f"MonitorOrchestrator initialized: "
            f"account={self.account}, partition={self.partition}"
        )

    def _load_config(self, config_file: str) -> dict:
        """Load configuration from YAML file"""
        config_path = Path(config_file)
        if not config_path.exists():
            logger.debug(f"Config file not found: {config_file}")
            return {}

        try:
            if yaml is None:
                logger.warning("PyYAML not available, using default config")
                return {}
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return config.get("slurm", {})
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return {}

    def deploy_prometheus(
        self,
        config: PrometheusConfig,
        targets: Dict[str, str],
        config_dir: Path,
        data_dir: Path,
    ) -> str:
        """
        Deploy Prometheus container as SLURM job

        Args:
            config: PrometheusConfig
            targets: Dict of {job_name: "host:port"}
            config_dir: Directory for Prometheus config
            data_dir: Directory for Prometheus data

        Returns:
            SLURM job ID
        """
        logger.info("Deploying Prometheus container")

        # Create Prometheus configuration
        if yaml is None:
            raise RuntimeError("PyYAML is required for Prometheus deployment")
            
        prom_config = {
            "global": {
                "scrape_interval": config.scrape_interval,
                "evaluation_interval": config.scrape_interval,
            },
            "scrape_configs": [],
        }

        # Add scrape configs for each target
        for job_name, target in targets.items():
            prom_config["scrape_configs"].append(
                {
                    "job_name": job_name,
                    "static_configs": [{"targets": [target]}],
                    "metrics_path": "/metrics",
                    "scrape_interval": config.scrape_interval,
                }
            )

        # Write config file
        config_file = config_dir / "prometheus.yml"
        with open(config_file, "w") as f:
            yaml.safe_dump(prom_config, f, sort_keys=False)

        logger.info(f"Created Prometheus config: {config_file}")

        # Build SLURM script
        script = self._build_prometheus_script(config, config_dir, data_dir)

        # Submit job
        job_id = self._submit_job(script, "prometheus")
        logger.info(f"Prometheus deployed with job ID: {job_id}")

        return job_id

    def _build_prometheus_script(
        self,
        config: PrometheusConfig,
        config_dir: Path,
        data_dir: Path,
    ) -> str:
        """Build SLURM batch script for Prometheus"""

        resources = config.resources
        partition = config.partition
        log_file = (
            self.log_directory
            / f"prometheus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        script = f"""#!/bin/bash -l

#SBATCH --job-name=prometheus
#SBATCH --output={log_file}
#SBATCH --error={log_file}
#SBATCH --time={self.time_limit}
#SBATCH --partition={partition}
#SBATCH --qos={self.qos}"""

        if self.account:
            script += f"\n#SBATCH --account={self.account}"

        script += f"""
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={resources.get('cpu_cores', 2)}
#SBATCH --mem={resources.get('memory_gb', 4)}G

echo "========================================="
echo "Prometheus Monitor Starting"
echo "========================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Partition: {partition}"
echo "Date: $(date)"
echo "========================================="

# Load modules
source /usr/share/lmod/lmod/init/bash
module load {self.module_env}
module load {self.apptainer_module}

# Setup directories
mkdir -p {config_dir}
mkdir -p {data_dir}
chmod 777 {data_dir}

# Pull image
IMAGE_CACHE="{self.image_cache_dir}"
mkdir -p "$IMAGE_CACHE"
IMAGE_NAME="prometheus_latest.sif"
IMAGE_FILE="${{IMAGE_CACHE}}/${{IMAGE_NAME}}"

if [ ! -f "$IMAGE_FILE" ]; then
    echo "Pulling Prometheus image..."
    apptainer pull "$IMAGE_FILE" {config.image}
fi

# Run Prometheus
echo "Starting Prometheus..."
apptainer exec \\
    --bind {config_dir}:/etc/prometheus \\
    --bind {data_dir}:/prometheus \\
    "$IMAGE_FILE" \\
    /bin/prometheus \\
    --config.file=/etc/prometheus/prometheus.yml \\
    --storage.tsdb.path=/prometheus \\
    --storage.tsdb.retention.time={config.retention_time} \\
    --web.listen-address=0.0.0.0:{config.port} &

PROM_PID=$!
echo "✓ Prometheus PID: $PROM_PID"

# Cleanup function
cleanup() {{
    echo "Shutting down Prometheus..."
    kill $PROM_PID 2>/dev/null || true
    wait $PROM_PID 2>/dev/null || true
    echo "✓ Prometheus stopped"
}}
trap cleanup EXIT INT TERM

# Wait for startup
sleep 10

if ! kill -0 $PROM_PID 2>/dev/null; then
    echo "✗ Prometheus died during startup"
    exit 1
fi

COMPUTE_NODE=$(hostname)
echo ""
echo "========================================="
echo "Prometheus Ready!"
echo "========================================="
echo "Web UI: http://${{COMPUTE_NODE}}:{config.port}"
echo "Targets: http://${{COMPUTE_NODE}}:{config.port}/targets"
echo "========================================="

# Keep alive
wait $PROM_PID
exit $?
"""
        return script

    def _submit_job(self, script_content: str, name: str) -> str:
        """Submit job to SLURM"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            script_path = f.name

        try:
            result = subprocess.run(
                ["sbatch", script_path],
                capture_output=True,
                text=True,
                check=True,
            )

            output = result.stdout.strip()
            job_id = output.split()[-1]

            logger.info(f"{name} job submitted: {job_id}")
            return job_id

        except subprocess.CalledProcessError as e:
            logger.error(f"Job submission failed: {e.stderr}")
            raise RuntimeError(f"Job submission failed: {e.stderr}")
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass

    def stop_component(self, job_id: str) -> bool:
        """Stop a monitoring component"""
        logger.info(f"Stopping component job: {job_id}")

        try:
            subprocess.run(
                ["scancel", job_id],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Component job cancelled: {job_id}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to cancel job: {e.stderr}")
            return False

    def get_component_status(self, job_id: str) -> MonitorStatus:
        """Get component status from SLURM"""
        try:
            result = subprocess.run(
                ["squeue", "-j", job_id, "--format=%T", "--noheader"],
                capture_output=True,
                text=True,
                check=True,
            )

            slurm_status = result.stdout.strip()

            status_map = {
                "PENDING": MonitorStatus.PENDING,
                "RUNNING": MonitorStatus.RUNNING,
                "COMPLETED": MonitorStatus.STOPPED,
                "FAILED": MonitorStatus.ERROR,
                "CANCELLED": MonitorStatus.STOPPED,
            }

            return status_map.get(slurm_status, MonitorStatus.STOPPED)

        except subprocess.CalledProcessError:
            return MonitorStatus.STOPPED

    def get_job_node(self, job_id: str) -> Optional[str]:
        """Get the node where a SLURM job is running"""
        try:
            result = subprocess.run(
                ["squeue", "-j", job_id, "--format=%N", "--noheader"],
                capture_output=True,
                text=True,
                check=True,
            )

            node = result.stdout.strip()
            return node if node else None

        except subprocess.CalledProcessError:
            logger.warning(f"Could not find node for job: {job_id}")
            return None
