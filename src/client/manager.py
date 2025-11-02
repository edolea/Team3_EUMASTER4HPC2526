from .recipe_loader import RecipeLoader
from .client_instance import ClientInstance, RunStatus
from .orchestrator import ClientOrchestrator


class ClientManager:
    def __init__(self, recipe_directory='../recipes/clients'):
        self.recipe_loader = RecipeLoader(recipe_directory=recipe_directory)
        self.clients = {}
        self._orchestrator = None

    @property
    def orchestrator(self):
        if self._orchestrator is None:
            self._orchestrator = ClientOrchestrator()
        return self._orchestrator

    def add_client(self, name, config):
        if name in self.clients:
            raise ValueError(f"Client {name} already exists")
        
        recipe = self.recipe_loader.load_recipe(config['recipe'])
        target_endpoint = config.get('endpoint') or recipe.target.get('endpoint')
        
        if not target_endpoint:
            raise ValueError("Target endpoint must be specified")
        
        client = ClientInstance(
            recipe_name=recipe.name,
            orchestrator_handle='local',
            target_endpoint=target_endpoint
        )
        
        self.clients[name] = client
        return client

    def remove_client(self, name):
        if name not in self.clients:
            return False
        
        client = self.clients[name]
        if client.status == RunStatus.RUNNING:
            client.stop()
        
        del self.clients[name]
        return True

    def list_available_clients(self):
        return self.recipe_loader.list_available_recipes()

    def get_client(self, name):
        return self.clients.get(name)

    def run_bench(self, name, runs=1):
        recipe = self.recipe_loader.load_recipe(name)
        target_endpoint = recipe.target.get('endpoint')
        
        if not target_endpoint:
            raise ValueError("Target endpoint must be specified in recipe")
        
        results = []
        for i in range(runs):
            client = ClientInstance(
                recipe_name=recipe.name,
                orchestrator_handle=f'run-{i}',
                target_endpoint=target_endpoint
            )
            
            try:
                job_id = self.orchestrator.submit(client, recipe, target_endpoint)
                client.orchestrator_handle = job_id
                client.start()
                
                self.clients[f"{name}-{client.id[:8]}"] = client
                results.append(client)
            
            except Exception as e:
                client.update_status(RunStatus.FAILED)
                raise RuntimeError(f"Failed to run benchmark: {e}")
        
        return results

    def stop_all(self):
        stopped = []
        for name, client in list(self.clients.items()):
            if client.status == RunStatus.RUNNING:
                try:
                    self.orchestrator.stop(client.orchestrator_handle)
                    client.stop()
                    stopped.append(name)
                except Exception:
                    pass
        return stopped

    def collect_metrics(self):
        metrics = []
        for name, client in self.clients.items():
            try:
                status = self.orchestrator.status(client.orchestrator_handle)
                client.update_status(status)
            except Exception:
                pass
            
            metrics.append({
                'client_name': name,
                **client.get_metrics()
            })
        
        return metrics
