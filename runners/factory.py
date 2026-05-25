from .standard_runner import StandardRunner
from .dfmm_runner import DFMMRunner
from .random_runner import RandomRunner
from .proposed_runner import ProposedRunner
from .extension_runner import ExtensionRunner   # 【提案手法】
from .compare_runner import CompareRunner       # 【比較実験】

_RUNNER_MAP = {
    # ----------------------------------------
    # 既存手法
    # ----------------------------------------
    "auto":      StandardRunner,   # MTWM (スケルトンツリー + CP-SAT)
    "dfmm":      DFMMRunner,       # 純粋 DFMM（最適化なし）
    "random":    RandomRunner,     # ランダム実験（targets.json を保存）
    "proposed":  ProposedRunner,   # 試作: 最多試薬フィルタ提案手法

    # ----------------------------------------
    # 【提案手法】拡張ノードによる廃棄液削減
    # ----------------------------------------
    "extension": ExtensionRunner,

    # ----------------------------------------
    # 【比較実験】同一ターゲットで MTWM vs Extension
    # ----------------------------------------
    "compare":   CompareRunner,
}

def get_runner(mode: str, config):
    runner_class = _RUNNER_MAP.get(mode)
    if not runner_class:
        valid = list(_RUNNER_MAP.keys())
        raise ValueError(f"Unknown mode: '{mode}'.  有効なモード: {valid}")
    return runner_class(config)