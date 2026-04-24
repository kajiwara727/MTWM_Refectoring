# core/solver/dto.py
from dataclasses import dataclass
from typing import List
from core.models import NodeAddress

@dataclass
class NodeFlowResult:
    """最適化後の各ノードの状態"""
    address: NodeAddress
    total_input: int
    concentration_state: List[int]       # 濃度状態 (旧: R)
    injected_reagent_volumes: List[int]  # 試薬注入量 (旧: r)
    waste_fluids: int = 0                # 廃棄液滴量

@dataclass
class EdgeFlowResult:
    """ノード間の液滴の移動（共有）状態"""
    source: NodeAddress
    target: NodeAddress
    volume: int

@dataclass
class OptimizationResult:
    """ソルバーが返す最終的な最適化結果"""
    objective_value: int
    total_waste_fluids: int
    nodes: List[NodeFlowResult]
    edges: List[EdgeFlowResult]
    execution_time: float = 0.0