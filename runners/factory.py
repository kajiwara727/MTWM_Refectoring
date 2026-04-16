from .standard_runner import StandardRunner
from .dfmm_runner import DFMMRunner
# インスタンス生成のロジックを隠蔽
# マップの定義
_RUNNER_MAP = {
    "auto": StandardRunner,
    "dfmm": DFMMRunner
}

def get_runner(mode: str, config):
    runner_class = _RUNNER_MAP.get(mode)
    if not runner_class:
        raise ValueError(f"Unknown Mode: '{mode}'")
    return runner_class(config)