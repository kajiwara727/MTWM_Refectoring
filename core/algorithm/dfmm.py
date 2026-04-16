import math
import copy
from typing import List, Dict, Tuple
from core.models import Target, MixingNode

# 合計値を上限値以下の掛け算に分解
def find_factors_for_sum(ratio_sum: int, max_factor: int) -> List[int]:
    """
    合計値を max_factor 以下の整数の積に分解
    """
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
            raise ValueError(
                f"合計値 {ratio_sum} は最大ミキサーサイズ {max_factor} 以下で因数分解できません。"
            )
            
    return sorted(factors, reverse=True)

def apply_auto_factors(targets: List[Target], max_mixer_size: int) -> List[Target]:
    """
    元のTargetリストをに
    factorsを付与した新しいTargetリストを返す
    """
    processed_targets = copy.deepcopy(targets)
    for target in processed_targets:
        target.factors = find_factors_for_sum(sum(target.ratios), max_mixer_size)
    return processed_targets

# =====================================================================
# 関数1: MTWM用（純粋な骨組みのみを作成）
# =====================================================================
def build_skeleton_tree(target: Target) -> Dict[Tuple[int, int], MixingNode]:
    """
    MTWM最適化プロセス用の関数。
    試薬の割り当てを行わず、純粋な接続関係（骨組み）のみを持つ MixingNode グラフを生成する。
    """
    if not target.factors:
        raise ValueError(f"Target '{target.name}' に factors が設定されていません。")

    factors = target.factors
    num_levels = len(factors)
    tree_nodes: Dict[Tuple[int, int], MixingNode] = {}
    values_to_process = list(target.ratios)
    nodes_from_below: List[MixingNode] = []

    for l in range(num_levels - 1, -1, -1):
        factor = factors[l]
        level_remainders = [v % factor for v in values_to_process]
        level_quotients = [v // factor for v in values_to_process]
        
        total_inputs = sum(level_remainders) + len(nodes_from_below)
        num_nodes_at_level = math.ceil(total_inputs / factor) if total_inputs > 0 else 0
        current_level_nodes: List[MixingNode] = []

        for k in range(num_nodes_at_level):
            # factor (target.factors[l]) をノードに保持させる
            node = MixingNode(id=(l, k), mixer_size=factor) 
            tree_nodes[node.id] = node
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

# =====================================================================
# 関数2: 純粋DFMM用（試薬の割り当てまで完結させる）
# =====================================================================
def build_dfmm_routing_tree(target: Target) -> Dict[Tuple[int, int], MixingNode]:
    """
    単一ターゲットのDFMM用の関数。
    骨組みの生成に加え、各ノードの dispense_inputs に試薬の注入スケジュールを記録する。
    """
    if not target.factors:
        raise ValueError(f"Target '{target.name}' に factors が設定されていません。")

    factors = target.factors
    num_levels = len(factors)
    tree_nodes: Dict[Tuple[int, int], MixingNode] = {}
    values_to_process = list(target.ratios)
    nodes_from_below: List[MixingNode] = []

    for l in range(num_levels - 1, -1, -1):
        factor = factors[l]
        level_remainders = [v % factor for v in values_to_process]
        level_quotients = [v // factor for v in values_to_process]
        
        total_inputs = sum(level_remainders) + len(nodes_from_below)
        num_nodes_at_level = math.ceil(total_inputs / factor) if total_inputs > 0 else 0
        current_level_nodes: List[MixingNode] = []

        # ノードの生成
        for k in range(num_nodes_at_level):
            node = MixingNode(id=(l, k))
            tree_nodes[node.id] = node
            current_level_nodes.append(node)

        # 子ノードの割り当てと、試薬の割り当て
        if num_nodes_at_level > 0:
            parent_idx = 0
            for child_node in nodes_from_below:
                parent_node = current_level_nodes[parent_idx]
                parent_node.children.append(child_node)
                parent_idx = (parent_idx + 1) % num_nodes_at_level

            # --- 試薬割り当てロジック ---
            reagents_to_dispense = []
            for reagent_idx, remainder in enumerate(level_remainders):
                reagents_to_dispense.extend([reagent_idx] * remainder)

            dispense_idx = 0
            for node in current_level_nodes:
                available_slots = factor - len(node.children)
                for _ in range(available_slots):
                    if dispense_idx < len(reagents_to_dispense):
                        node.dispense_inputs.append(reagents_to_dispense[dispense_idx])
                        dispense_idx += 1
                    else:
                        node.dispense_inputs.append(-1) # バッファ/ダミー液滴

        nodes_from_below = current_level_nodes
        values_to_process = level_quotients
        
    return tree_nodes

# =====================================================================
# 共通: P値の計算
# =====================================================================
def calculate_p_values(tree_nodes: Dict[Tuple[int, int], MixingNode], factors: List[int]) -> None:
    memo = {}

    def get_p_for_node(node: MixingNode) -> int:
        if node.id in memo: return memo[node.id]
        level = node.id[0]
        if not node.children:
            p = math.prod(factors[level:])
        else:
            p = max(get_p_for_node(child) for child in node.children) * factors[level]
        memo[node.id] = p
        node.p_value = p
        return p

    for node in tree_nodes.values():
        get_p_for_node(node)