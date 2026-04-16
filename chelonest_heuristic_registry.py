import os
import importlib

class HeuristicRegistry:
    HEURISTICS = {}
    _processor = None

    def __init__(self):
        print("Heuristics: registry created")

    def register(self, name):
        self._processor.log("registering " + name)
        def wrapper(cls):
            self.HEURISTICS[name] = cls
            return cls
        return wrapper
        
    def load_heuristic_instances(self, config):
        instances = []

        for hconf in config:
            htype = hconf["type"]
            
            if "enabled" in hconf and hconf["enabled"] == False:
                continue
                
            cls = self.HEURISTICS[htype]

            params = {}
            
            if "parameters" in hconf:
                params = {k: v for k, v in hconf["parameters"].items()}

            params["processor"] = self._processor
            if "name" not in params:
                params["name"] = hconf["type"]
             
            instances.append(cls(**params))

        return instances

    def load_heuristic_modules(self):
        self._processor.log("begin loading plugins")
        folder = "heuristics"
        for filename in os.listdir(folder):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = f"{folder}.{filename[:-3]}"
                self._processor.log("attempting to load " + module_name)
                importlib.import_module(module_name)
        self._processor.log("done loading plugins")

registry = HeuristicRegistry()
register = registry.register