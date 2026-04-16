# core/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

@dataclass
class Target:
    name: str
    ratios: List[int]
    # factorsがNoneを返しても良いように
    factors: Optional[List[int]] = None

@dataclass
class MixingNode:
    id: Tuple[int, int]  # (level, k) のタプル
    mixer_size: int = 0
    children: List['MixingNode'] = field(default_factory=list) #  入力元,どこから液滴を運んでくるかのリスト
    p_value: Optional[int] = None # 液滴の重み
    dispense_inputs: List[int] = field(default_factory=list) # 試薬割り当て用
    # 各ノードはそれぞれ比率が定められているはずなのでそのノードの比率を表す情報が必要かも