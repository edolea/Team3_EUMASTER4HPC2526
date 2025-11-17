from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

class PrometheusClient:
    """
    Minimal wrapper around a Prometheus process.
    By default we don't actually spawn Prometheus unless a `prometheus_bin` is provided.
    This keeps the module safe to import/run on systems without Prometheus.
    """

    def __init__(self, workdir: str = ".prometheus") -> None:
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._proc: Optional[subprocess.Popen] = None
        self._config_path: Optional[Path] = None
        self._url: Optional[str] = None

    @property
    def url(self) -> Optional[str]:
        return self._url

    def deploy(self, targets: List[str], config: Dict[str, Any], prometheus_bin: Optional[str] = None, port: int = 9090) -> str:
        if yaml is None:
            logger.warning("PyYAML not installed; returning a fake URL for Prometheus.")
            self._url = f"http://localhost:{port}"
            return self._url

        # Write config to file
        self._config_path = self.workdir / "prometheus.yml"
        self._config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        self._url = f"http://localhost:{port}"

        if prometheus_bin:
            # Start Prometheus as a subprocess
            logger.info("Starting Prometheus subprocess...")
            self._proc = subprocess.Popen(
                [prometheus_bin, f"--config.file={self._config_path}", f"--web.listen-address=:{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info(f"Prometheus started on {self._url}")
        else:
            logger.info("Prometheus binary not provided. Skipping actual process spawn.")
        return self._url

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            logger.info("Stopping Prometheus subprocess...")
            self._proc.terminate()
            self._proc.wait(timeout=10)
            logger.info("Prometheus stopped.")
        self._proc = None

    def query(self, query: str) -> Dict[str, Any]:
        # For a self-contained module, we stub the query.
        logger.info(f"Stub query to Prometheus: {query}")
        return {"status": "success", "data": {"resultType": "vector", "result": []}}
