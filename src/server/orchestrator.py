"""SLURM orchestrator for server deployments."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

from .server_instance import ServerStatus


class ServerOrchestrator:
    """Wraps SLURM commands used to manage server jobs."""

    def __init__(
        self,
        *,
        partition: str | None = None,
        account: str | None = None,
        qos: str | None = None,
        time_limit: str | None = None,
    ) -> None:
        load_dotenv()

        self.account = account or os.getenv("SLURM_ACCOUNT")
        self.partition = partition or os.getenv("SLURM_PARTITION", "cpu")
        self.qos = qos or os.getenv("SLURM_QOS", "default")
        self.time_limit = time_limit or os.getenv("SLURM_TIME_LIMIT", "04:00:00")

        if not self.account:
            raise ValueError("SLURM account must be provided (set SLURM_ACCOUNT or pass account=)")

    # ------------------------------------------------------------------
    def submit(self, instance, recipe) -> str:
        script_content = self._build_batch_script(instance, recipe)
        return self._submit_job(script_content)

    # ------------------------------------------------------------------
    def stop(self, job_id: str) -> bool:
        try:
            subprocess.run(
                ["scancel", job_id],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    # ------------------------------------------------------------------
    def status(self, job_id: str) -> Dict[str, any]:
        try:
            result = subprocess.run(
                ["squeue", "-j", job_id, "--format=%T,%N,%P", "--noheader"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            return {"status": ServerStatus.COMPLETED}

        status_map: Dict[str, ServerStatus] = {
            "PENDING": ServerStatus.SUBMITTED,
            "CONFIGURING": ServerStatus.STARTING,
            "RUNNING": ServerStatus.RUNNING,
            "COMPLETED": ServerStatus.COMPLETED,
            "COMPLETING": ServerStatus.COMPLETED,
            "FAILED": ServerStatus.FAILED,
            "TIMEOUT": ServerStatus.FAILED,
            "CANCELLED": ServerStatus.CANCELED,
        }

        output = result.stdout.strip().splitlines()
        if not output:
            return {"status": ServerStatus.COMPLETED}

        parts = output[0].split(",")
        slurm_status, node, ports_str = parts[0], parts[1], parts[2]

        status = status_map.get(slurm_status, ServerStatus.RUNNING)
        return {"status": status, "node": node, "ports": ports_str}

    # ------------------------------------------------------------------
    def _build_batch_script(self, instance, recipe) -> str:
        resources = recipe.resources
        cpu_cores = resources.get("cpu_cores", 1)
        memory_gb = resources.get("memory_gb", 4)
        gpu_count = resources.get("gpu_count", 0)
        partition = resources.get("partition", self.partition)

        working_dir = recipe.working_directory or os.getcwd()
        working_path = Path(working_dir)
        if not working_path.is_absolute():
            working_path = Path(os.getcwd()) / working_path

        env_exports = "\n".join(
            f'export {key}="{value}"'
            for key, value in recipe.env.items()
        )

        if env_exports:
            env_exports += "\n"

        port_info = " ".join(str(p) for p in recipe.ports)

        # Build GPU directive if needed
        gpu_directive = f"\n#SBATCH --gres=gpu:{gpu_count}" if gpu_count > 0 else ""

        script = f"""#!/bin/bash -l

#SBATCH --job-name={recipe.name}_{instance.id[:8]}
#SBATCH --time={self.time_limit}
#SBATCH --qos={self.qos}
#SBATCH --partition={partition}
#SBATCH --account={self.account}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={cpu_cores}
#SBATCH --mem={memory_gb}G{gpu_directive}

echo "========================================="
echo "Server Deployment"
echo "========================================="
echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = {working_path}"
echo "Job ID            = $SLURM_JOB_ID"
echo "Instance ID       = {instance.id}"
echo "Recipe            = {recipe.name}"
echo "Ports             = {port_info}"
echo "========================================="

cd {working_path}

{env_exports}{recipe.service.get('command')}

EXIT_CODE=$?

echo ""
echo "========================================="
echo "Service exited with code $EXIT_CODE"
echo "========================================="

exit $EXIT_CODE
"""
        return script

    # ------------------------------------------------------------------
    def _submit_job(self, script_content: str) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as handle:
            handle.write(script_content)
            script_path = handle.name

        try:
            result = subprocess.run(
                ["sbatch", script_path],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else ""
            raise RuntimeError(f"Job submission failed: {stderr}") from exc
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

        output = result.stdout.strip().split()
        if not output:
            raise RuntimeError("Unexpected empty response from sbatch")

        return output[-1]


__all__ = ["ServerOrchestrator"]
