import subprocess
import tempfile
import os
from pathlib import Path


class ClientOrchestrator:
    def __init__(self, partition=None, account=None, qos=None, time_limit=None):
        from dotenv import load_dotenv
        load_dotenv()
        
        self.account = account or os.getenv('SLURM_ACCOUNT')
        self.partition = partition or os.getenv('SLURM_PARTITION', 'cpu')
        self.qos = qos or os.getenv('SLURM_QOS', 'default')
        self.time_limit = time_limit or os.getenv('SLURM_TIME_LIMIT', '00:30:00')
        
        if not self.account:
            raise ValueError("SLURM account must be provided")

    def submit(self, run, recipe, target_endpoint):
        script_content = self._build_batch_script(run, recipe, target_endpoint)
        
        try:
            job_id = self._submit_job(script_content)
            return job_id
        except Exception as e:
            raise RuntimeError(f"SLURM submission failed: {e}")

    def stop(self, job_id):
        try:
            subprocess.run(
                ['scancel', job_id],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def status(self, job_id):
        try:
            result = subprocess.run(
                ['squeue', '-j', job_id, '--format=%T', '--noheader'],
                capture_output=True,
                text=True,
                check=True,
            )
            
            from .client_instance import RunStatus
            slurm_status = result.stdout.strip()
            
            status_map = {
                'PENDING': RunStatus.SUBMITTED,
                'RUNNING': RunStatus.RUNNING,
                'COMPLETED': RunStatus.COMPLETED,
                'FAILED': RunStatus.FAILED,
                'CANCELLED': RunStatus.CANCELED,
                'TIMEOUT': RunStatus.FAILED,
            }
            
            return status_map.get(slurm_status, RunStatus.COMPLETED)
        
        except subprocess.CalledProcessError:
            from .client_instance import RunStatus
            return RunStatus.COMPLETED

    def _build_batch_script(self, run, recipe, target_endpoint):
        resources = recipe.orchestration.get('resources', {})
        cpu_cores = resources.get('cpu_cores', 1)
        memory_gb = resources.get('memory_gb', 4)
        
        workload_cmd = self._build_workload_command(recipe, target_endpoint, run)
        
        script = f"""#!/bin/bash -l

#SBATCH --job-name={recipe.name}_{run.id[:8]}
#SBATCH --time={self.time_limit}
#SBATCH --qos={self.qos}
#SBATCH --partition={self.partition}
#SBATCH --account={self.account}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={cpu_cores}
#SBATCH --mem={memory_gb}G

echo "========================================="
echo "Benchmark Client"
echo "========================================="
echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = $(pwd)"
echo "Job ID            = $SLURM_JOB_ID"
echo "Run ID            = {run.id}"
echo "Recipe            = {recipe.name}"
echo "Target            = {target_endpoint}"
echo "========================================="

cd {os.getcwd()}

OUTPUT_DIR="{recipe.output.get('destination', './results')}"
mkdir -p "$OUTPUT_DIR"

echo ""
echo "Starting benchmark workload..."
{workload_cmd}

EXIT_CODE=$?

echo ""
echo "========================================="
echo "Benchmark Completed"
echo "========================================="
echo "Exit Code: $EXIT_CODE"
echo "Results:   $OUTPUT_DIR"
echo "========================================="

exit $EXIT_CODE
"""
        return script

    def _build_workload_command(self, recipe, target_endpoint, run):
        output_dir = recipe.output.get('destination', './results')
        output_file = f"{output_dir}/{recipe.name}_{run.id[:8]}_results.json"
        
        pattern = recipe.workload.get('pattern', 'closed-loop')
        duration = recipe.workload.get('duration_seconds', 60)
        concurrent_users = recipe.workload.get('concurrent_users', 1)
        think_time = recipe.workload.get('think_time_ms', 0)
        requests_per_user = recipe.workload.get('requests_per_user', 100)
        
        # Get payload from recipe (if defined) or build from dataset
        payload = recipe.payload
        
        # If no explicit payload, try to build from dataset configuration
        if not payload and recipe.dataset:
            payload = self._build_payload_from_dataset(recipe.dataset, target_endpoint)
        
        import json
        payload_json = json.dumps(payload) if payload else '{}'
        
        # Get headers from recipe
        headers = recipe.headers if hasattr(recipe, 'headers') else {}
        headers_json = json.dumps(headers) if headers else '{}'
        
        cmd = f"""python -m src.client.workload_runner \\
    --endpoint "{target_endpoint}" \\
    --pattern "{pattern}" \\
    --duration {duration} \\
    --concurrent-users {concurrent_users} \\
    --think-time {think_time} \\
    --requests-per-user {requests_per_user} \\
    --payload '{payload_json}' \\
    --headers '{headers_json}' \\
    --output "{output_file}"
"""
        return cmd
    
    def _build_payload_from_dataset(self, dataset, target_endpoint):
        """Build request payload from dataset configuration.
        This is a helper for synthetic datasets - adjust endpoint and payload based on dataset type.
        """
        dataset_type = dataset.get('type', 'synthetic')
        params = dataset.get('params', {})
        
        # For synthetic datasets, try to infer the service type and build appropriate payload
        if 'model_name' in params:
            # Looks like an LLM service (vLLM, Ollama, etc.)
            # These typically use /v1/completions or /v1/chat/completions
            return {
                "model": params.get('model_name', 'default'),
                "prompt": params.get('prompt', 'Once upon a time'),
                "max_tokens": params.get('max_tokens', 20),
                "temperature": params.get('temperature', 0.7),
                "top_p": params.get('top_p', 1.0)
            }
        
        # Default: return params as-is
        return params

    def _submit_job(self, script_content):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            result = subprocess.run(
                ['sbatch', script_path],
                capture_output=True,
                text=True,
                check=True,
            )
            
            output = result.stdout.strip()
            job_id = output.split()[-1]
            return job_id
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Job submission failed: {e.stderr}")
        
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass
