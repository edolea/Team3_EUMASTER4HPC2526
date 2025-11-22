import yaml
from pathlib import Path


class ClientRecipe:
    def __init__(self, name, target, workload, dataset=None, orchestration=None, 
                 output=None, description=None, headers=None, payload=None, service_name=None):
        self.name = name
        self.target = target
        self.workload = workload
        self.dataset = dataset or {}
        self.orchestration = orchestration or {}
        self.output = output or {}
        self.description = description
        self.headers = headers or {}
        self.payload = payload or {}
        self.service_name = service_name or name
        self.image = None
        self.resources = orchestration.get('resources', {}) if orchestration else {}
        self.endpoints = target.get('endpoint') if target else None
        self.ports = target.get('port') if target else None

    def validate(self):
        if not self.name:
            raise ValueError("Recipe name is required")
        if not self.target:
            raise ValueError("Target is required")
        if not self.workload:
            raise ValueError("Workload is required")
        
        protocol = self.target.get('protocol', 'http')
        if protocol not in ['http', 'https']:
            raise ValueError(f"Unsupported protocol: {protocol}")
        
        pattern = self.workload.get('pattern', 'closed-loop')
        if pattern not in ['open-loop', 'closed-loop']:
            raise ValueError(f"Unsupported pattern: {pattern}")
        
        if self.workload.get('duration_seconds', 0) <= 0:
            raise ValueError("duration_seconds must be positive")
        
        return True

    @classmethod
    def from_yaml(cls, yaml_path):
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Recipe file not found: {yaml_path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        recipe = cls(
            name=data['name'],
            target=data.get('target', {}),
            workload=data.get('workload', {}),
            dataset=data.get('dataset', {}),
            orchestration=data.get('orchestration', {}),
            output=data.get('output', {}),
            description=data.get('description'),
            headers=data.get('headers', {}),
            payload=data.get('payload', {}),
            service_name=data.get('service_name')
        )
        
        recipe.validate()
        return recipe

