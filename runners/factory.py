from .standard_runner import StandardRunner
from .dfmm_runner import DFMMRunner
from .random_runner import RandomRunner

_RUNNER_MAP = {
    "auto": StandardRunner,
    "dfmm": DFMMRunner,
    "random": RandomRunner
}

def get_runner(mode: str, config):
    runner_class = _RUNNER_MAP.get(mode)
    if not runner_class:
        raise ValueError(f"Unknown Mode: '{mode}'")
    return runner_class(config)