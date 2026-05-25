# core/algorithm/reachability.py
from collections import Counter
from typing import Dict, List, Tuple
from core.models import MixingNode, NodeAddress, Target

class ReachabilityAnalyzer:
    """
    アイデア1: スケルトン構造から、各ノードの『試薬調整を考慮した濃度境界』を解析する
    """
    @staticmethod
    def run(tree_structures: List[Dict[NodeAddress, MixingNode]], targets: List[Target]):
        num_reagents = len(targets[0].ratios)
        for m, tree in enumerate(tree_structures):
            # 1. ボトムアップ: 構造上「作りうる」濃度の最大・最小
            nodes = sorted(tree.values(), key=lambda n: n.address.level, reverse=True)
            for node in nodes:
                ReachabilityAnalyzer._calc_supply_limit(node, num_reagents)

            # 2. トップダウン: ターゲット達成のために「入力が満たすべき」濃度範囲
            total_ratio = sum(targets[m].ratios)
            target_conc = [r / total_ratio for r in targets[m].ratios]
            for n in [v for v in tree.values() if v.address.level == 0]:
                n.demand_intervals = {t: (target_conc[t], target_conc[t]) for t in range(num_reagents)}
            
            nodes_td = sorted(tree.values(), key=lambda n: n.address.level)
            for node in nodes_td:
                ReachabilityAnalyzer._propagate_demand(node, num_reagents)

    @staticmethod
    def _calc_supply_limit(node: MixingNode, num_reagents: int):
        M = node.mixer_size
        # DFMMで割り当てられた試薬ユニット（調整可能な最大予算 U_r）
        budget = Counter(node.reagent_dispensations)
        for t in range(num_reagents):
            u_rt = budget[t] # 試薬 t の最大スロット数
            if not node.children:
                # リーフ: 試薬 t を 0～u_rt 使うことで、濃度は 0.0 ～ u_rt/M になる
                node.supply_intervals[t] = (0.0, u_rt / M)
            else:
                # 子ノードの出力範囲の合計に、自身の試薬調整幅を上乗せ
                min_in = sum(c.supply_intervals[t][0] for c in node.children) / M
                # 他の空きスロット（共有分）が最大濃度(1.0)である可能性を考慮
                free_slots = M - len(node.children)
                max_in = (sum(c.supply_intervals[t][1] for c in node.children) + free_slots) / M
                node.supply_intervals[t] = (min_in, max_in)

    @staticmethod
    def _propagate_demand(node: MixingNode, num_reagents: int):
        if not node.children: return
        M = node.mixer_size
        for t in range(num_reagents):
            d_min, d_max = node.demand_intervals[t]
            for child in node.children:
                # 他の入力がすべて最大/最小のとき、この子がターゲット達成に寄与できる範囲
                # 判定を厳しくしすぎないよう、物理的な希釈限界に基づいて算出
                other_max_sum = (M - 1) # child以外のM-1スロットがすべて1.0(純試薬)の場合
                req_min = max(0.0, M * d_min - other_max_sum)
                req_max = min(1.0, M * d_max) # 他がすべて0.0の場合
                child.demand_intervals[t] = (req_min, req_max)