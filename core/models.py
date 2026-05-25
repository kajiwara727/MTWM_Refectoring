# core/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass(frozen=True)
class NodeAddress:
    """
    ノードの論理的な位置を特定するアドレス。
    これにより (m, l, k) のタプルによる曖昧さを排除し、型安全性を担保します。
    """
    target_id: int  # ターゲットのインデックス (旧: m)
    level: int      # ツリーの深さ・レベル (旧: l)
    index: int      # そのレベルにおけるノードのインデックス (旧: k)

@dataclass(frozen=True)
class ExtensionNodeAddress:
    """
    【提案手法】拡張ノードの論理的なアドレス。
    論文の記法 u_{p,h} に対応。
    p: 液滴の重み（droplet_weight）
    h: 同じ重みを持つ拡張ノードの中でのインデックス
    """
    weight: int  # 液滴の重み p
    index: int   # 拡張ノードのインデックス h

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

@dataclass
class ExtensionNode:
    """
    【提案手法】拡張ノード u_{p,h}。
    同じ重み p を持つ2つの中間ノードを 1:1 で混合し、
    同じ重みの新しい中間液滴を生成する（論文 Section III）。

    - mixer_size は常に 2（1:1 混合）
    - droplet_weight は常に p（入力と同じ重み）
    - input_1, input_2 は重みが等しい中間ノードのアドレス
    """
    address: ExtensionNodeAddress
    input_1: NodeAddress                    # 入力ノード1
    input_2: NodeAddress                    # 入力ノード2
    mixer_size: int = 2                     # 常に 2（1:1混合）
    droplet_weight: int = 0                 # = address.weight

    def __post_init__(self):
        self.droplet_weight = self.address.weight