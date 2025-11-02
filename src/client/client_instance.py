import uuid
from datetime import datetime
from enum import Enum


class RunStatus(Enum):
    SUBMITTED = 'submitted'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELED = 'canceled'


class ClientInstance:
    def __init__(self, recipe_name, orchestrator_handle, target_endpoint=None):
        self.id = str(uuid.uuid4())
        self.recipe_name = recipe_name
        self.orchestrator_handle = orchestrator_handle
        self.status = RunStatus.SUBMITTED
        self.endpoints = target_endpoint
        self.created_at = datetime.now()
        self.completed_at = None
        self.metrics = {}

    def to_dict(self):
        return {
            'id': self.id,
            'recipe_name': self.recipe_name,
            'status': self.status.value,
            'endpoints': self.endpoints,
            'orchestrator_handle': self.orchestrator_handle,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    def get_metrics(self):
        duration = self._get_duration()
        return {
            'run_id': self.id,
            'recipe_name': self.recipe_name,
            'status': self.status.value,
            'duration_seconds': duration,
            'endpoint': self.endpoints,
            **self.metrics
        }

    def update_status(self, new_status):
        self.status = new_status
        if new_status in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED]:
            self.completed_at = datetime.now()

    def start(self):
        self.update_status(RunStatus.RUNNING)

    def stop(self):
        self.update_status(RunStatus.CANCELED)

    def _get_duration(self):
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return (datetime.now() - self.created_at).total_seconds()
