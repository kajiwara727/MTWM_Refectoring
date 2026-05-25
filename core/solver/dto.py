# core/solver/dto.py
from dataclasses import dataclass, field
from typing import List, Tuple
from core.models import NodeAddress, ExtensionNodeAddress


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
class ExtensionNodeFlowResult:
    """【提案手法】最適化後の各拡張ノードの状態"""
    address: ExtensionNodeAddress
    input_1: NodeAddress
    input_2: NodeAddress
    concentration_state: List[int]                   # C^k_{p,h}
    waste_fluids: int = 0                            # 拡張ノード自身の廃棄液滴
    outgoing_volumes: List[Tuple[NodeAddress, int]] = field(default_factory=list)
    # (宛先ノードアドレス, 送出量 z) のリスト


@dataclass
class OptimizationResult:
    """ソルバーが返す最終的な最適化結果"""
    objective_value: int
    total_waste_fluids: int
    nodes: List[NodeFlowResult]
    edges: List[EdgeFlowResult]
    execution_time: float = 0.0
    extension_nodes: List[ExtensionNodeFlowResult] = field(default_factory=list)  # 【提案手法】