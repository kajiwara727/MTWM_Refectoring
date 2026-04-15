# core/__init__.py

# ===== Models (データ構造) =====
from .models import Target, MixingNode

# ===== Algorithm (DFMMの純粋な計算ロジック) =====
from .algorithm.dfmm import (
    apply_auto_factors,
    build_skeleton_tree,
    build_dfmm_routing_tree,
    calculate_p_values
)

# 外部モジュール（Runners, Solversなど）に公開するAPI
__all__ = [
    # Models
    "Target",
    "MixingNode",
    
    # Algorithm
    "apply_auto_factors",
    "build_skeleton_tree",
    "build_dfmm_routing_tree",
    "calculate_p_values",
]