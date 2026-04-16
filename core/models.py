# core/models.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class NodeAddress:
    """
    ノードの論理的な位置を特定するアドレス。
    これにより (m, l, k) のタプルによる曖昧さを排除し、型安全性を担保します。
    """
    target_id: int  # ターゲットのインデックス (旧: m)
    level: int      # ツリーの深さ・レベル (旧: l)
    index: int      # そのレベルにおけるノードのインデックス (旧: k)

@dataclass
class Target:
    """
    作成目標となる液滴（ターゲット）の定義
    """
    name: str
    ratios: List[int]
    factors: Optional[List[int]] = None

@dataclass
class MixingNode:
    """
    デジタルマイクロフルイディクスにおける混合操作の単位（ノード）
    """
    address: NodeAddress
    mixer_size: int = 0
    children: List['MixingNode'] = field(default_factory=list) # 入力元（どこから液滴を運んでくるか）
    droplet_weight: Optional[int] = None # 液滴の重み/濃度係数 (旧: p_value)
    reagent_dispensations: List[int] = field(default_factory=list) # 試薬の注入スケジュール (旧: dispense_inputs)