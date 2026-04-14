from .base_runner import BaseRunner
from core.algorithm.dfmm import apply_auto_factors

class StandardRunner(BaseRunner):
    def run(self):
        targets_config = self.config.TARGETS

        # DFMMの処理
        apply_auto_factors(targets_config, self.config.MAX_MIXER_SIZE)
        output_dir = self.get_directory_name()