# core/__init__.py

# ===== Models (データ構造) =====
from .models import Target, MixingNode, NodeAddress, ExtensionNodeAddress, ExtensionNode

# ===== Algorithm (DFMMの純粋な計算ロジック) =====
from .algorithm.dfmm import (
    apply_auto_factors,
    build_complete_dfmm_tree,
    build_complete_skeleton_tree,
)

# ===== Algorithm (【提案手法】拡張ノード生成) =====
from .algorithm.extension import generate_extension_nodes, describe_extension_nodes

# 外部モジュール（Runners, Solversなど）に公開するAPI
__all__ = [
    # Models
    "Target",
    "MixingNode",
    "NodeAddress",
    "ExtensionNodeAddress",   # 【提案手法】
    "ExtensionNode",          # 【提案手法】

    # Algorithm
    "apply_auto_factors",
    "build_complete_dfmm_tree",
    "build_complete_skeleton_tree",

    # Algorithm (拡張ノード)
    "generate_extension_nodes",   # 【提案手法】
    "describe_extension_nodes",   # 【提案手法】
]