import os
from abc import ABC, abstractmethod

class BaseRunner(ABC):
    def __init__(self, config):
        self.config = config
        # self.engine = ExecutionEngine(config)
    
    @abstractmethod
    def run(self): pass

    def get_directory_name(self):
        run_name = self.config.RUN_NAME
        mode_name = self.config.RUNNER_MODE

        base_name = f"{run_name}_{mode_name}"
        output_dir = base_name
        counter = 1

        while os.path.isdir(output_dir):
            output_dir = f"{base_name}_{counter}"
            counter += 1
            
        return output_dir