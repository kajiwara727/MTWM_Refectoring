import math
import copy
from typing import List, Dict
from core.models import Target, MixingNode, NodeAddress

def build_complete_skeleton_tree(target: Target, target_id: int) -> Dict[NodeAddress, MixingNode]:
    """
    MTWM用: ベースツリーの構築と重み計算を一度に行い、
    完全に初期化されたツリーを返します。
    """
    tree_nodes = build_skeleton_tree(target, target_id)
    # 内部で副作用が発生しても、外部には完成品だけを返すのでカプセル化される
    calculate_droplet_weights(tree_nodes, target.factors)
    return tree_nodes

def build_complete_dfmm_tree(target: Target, target_id: int) -> Dict[NodeAddress, MixingNode]:
    """
    純粋DFMM用: ルーティングツリーの構築と重み計算を一度に行います。
    """
    tree_nodes = build_dfmm_routing_tree(target, target_id)
    calculate_droplet_weights(tree_nodes, target.factors)
    return tree_nodes

def find_factors_for_sum(ratio_sum: int, max_factor: int) -> List[int]:
    if ratio_sum <= 1: 
        return []
    n = ratio_sum
    factors = []
    while n > 1:
        found_divisor = False
        for d in range(max_factor, 1, -1):
            if n % d == 0:
                factors.append(d)
                n //= d
                found_divisor = True
                break
        if not found_divisor:
            raise ValueError(f"合計値 {ratio_sum} は最大ミキサーサイズ {max_factor} 以下で因数分解できません。")
    return sorted(factors, reverse=True)

def apply_auto_factors(targets: List[Target], max_mixer_size: int) -> List[Target]:
    processed_targets = copy.deepcopy(targets)
    for target in processed_targets:
        target.factors = find_factors_for_sum(sum(target.ratios), max_mixer_size)
    return processed_targets

def _build_base_tree(target: Target, target_id: int) -> Dict[NodeAddress, MixingNode]:
    """共通のツリー構築ロジック（骨組みの生成と親子関係の構築のみ）"""
    if not target.factors:
        raise ValueError(f"Target '{target.name}' に factors が設定されていません。")

    factors = target.factors
    num_levels = len(factors)
    tree_nodes: Dict[NodeAddress, MixingNode] = {}
    values_to_process = list(target.ratios)
    nodes_from_below: List[MixingNode] = []

    for level in range(num_levels - 1, -1, -1):
        factor = factors[level]
        level_remainders = [v % factor for v in values_to_process]
        level_quotients = [v // factor for v in values_to_process]
        
        total_inputs = sum(level_remainders) + len(nodes_from_below)
        num_nodes_at_level = math.ceil(total_inputs / factor) if total_inputs > 0 else 0
        current_level_nodes: List[MixingNode] = []

        for index in range(num_nodes_at_level):
            address = NodeAddress(target_id=target_id, level=level, index=index)
            node = MixingNode(address=address, mixer_size=factor) 
            tree_nodes[address] = node
            current_level_nodes.append(node)

        if num_nodes_at_level > 0:
            parent_idx = 0
            for child_node in nodes_from_below:
                parent_node = current_level_nodes[parent_idx]
                parent_node.children.append(child_node)
                parent_idx = (parent_idx + 1) % num_nodes_at_level

        nodes_from_below = current_level_nodes
        values_to_process = level_quotients
        
    return tree_nodes

def build_skeleton_tree(target: Target, target_id: int) -> Dict[NodeAddress, MixingNode]:
    """MTWM用：ベースツリーをそのまま返す"""
    return _build_base_tree(target, target_id)

def build_dfmm_routing_tree(target: Target, target_id: int) -> Dict[NodeAddress, MixingNode]:
    """純粋DFMM用：ベースツリーを構築後、試薬割り当てロジックのみを追加適用する"""
    tree_nodes = _build_base_tree(target, target_id)
    factors = target.factors
    values_to_process = list(target.ratios)

    for level in range(len(factors) - 1, -1, -1):
        factor = factors[level]
        level_remainders = [v % factor for v in values_to_process]
        
        reagents_to_dispense = []
        for reagent_idx, remainder in enumerate(level_remainders):
            reagents_to_dispense.extend([reagent_idx] * remainder)
            
        current_level_nodes = [node for addr, node in tree_nodes.items() if addr.level == level]
        current_level_nodes.sort(key=lambda n: n.address.index)

        dispense_idx = 0
        for node in current_level_nodes:
            available_slots = factor - len(node.children)
            for _ in range(available_slots):
                if dispense_idx < len(reagents_to_dispense):
                    node.reagent_dispensations.append(reagents_to_dispense[dispense_idx])
                    dispense_idx += 1
                else:
                    node.reagent_dispensations.append(-1)
                    
        values_to_process = [v // factor for v in values_to_process]
        
    return tree_nodes

def calculate_droplet_weights(tree_nodes: Dict[NodeAddress, MixingNode], factors: List[int]) -> None:
    memo = {}
    def get_weight_for_node(node: MixingNode) -> int:
        if node.address in memo: return memo[node.address]
        level = node.address.level
        if not node.children:
            weight = math.prod(factors[level:])
        else:
            weight = max(get_weight_for_node(child) for child in node.children) * factors[level]
        memo[node.address] = weight
        node.droplet_weight = weight
        return weight
    for node in tree_nodes.values():
        get_weight_for_node(node)