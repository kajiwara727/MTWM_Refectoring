# core/algorithm/extension.py
"""
【提案手法】拡張ノード生成ロジック（論文 Section III-B）

同じ重み p (> max_mixer_size) を持つ中間ノードを
順番にペアリングし、拡張ノード u_{p,h} を生成する。

アルゴリズム概要:
  1. 全ツリーから中間ノード（level > 0）を収集し weight でグループ化
  2. weight > M のグループのみ対象（コスト削減効果が大きいため）
  3. K_p = ceil(N_p / 2) 個の拡張ノードを生成
  4. ペアリング: (d1,d2), (d3,d4), ..., N_p が奇数なら最後は (d_{N_p}, d_1)
"""

import math
from collections import defaultdict
from typing import List, Dict

from core.models import NodeAddress, MixingNode, ExtensionNode, ExtensionNodeAddress


def generate_extension_nodes(
    tree_structures: List[Dict[NodeAddress, MixingNode]],
    max_mixer_size: int,
) -> List[ExtensionNode]:
    """
    ツリー構造から拡張ノードを生成する。

    Args:
        tree_structures: 各ターゲットのノード辞書 [NodeAddress -> MixingNode] のリスト
        max_mixer_size:  最大ミキサーサイズ M

    Returns:
        拡張ノードのリスト（生成順）
    """
    # -------------------------------------------------------------------
    # Step 1: 中間ノード（level > 0）を droplet_weight でグループ化
    #         ただし droplet_weight > M のもののみ対象（論文の条件 1）
    # -------------------------------------------------------------------
    nodes_by_weight: Dict[int, List[NodeAddress]] = defaultdict(list)

    for tree in tree_structures:
        for addr, node in tree.items():
            if addr.level > 0 and node.droplet_weight is not None:
                if node.droplet_weight > max_mixer_size:
                    nodes_by_weight[node.droplet_weight].append(addr)

    # -------------------------------------------------------------------
    # Step 2: 各グループで拡張ノードを生成（N_p >= 2 が条件）
    # -------------------------------------------------------------------
    extension_nodes: List[ExtensionNode] = []

    for p, addrs in sorted(nodes_by_weight.items()):  # 重みの昇順で処理（再現性のため）
        N_p = len(addrs)
        if N_p < 2:
            continue  # 2ノード未満は拡張ノードを作れない

        K_p = math.ceil(N_p / 2)  # 式 (9): K_p = ceil(N_p / 2)

        for h in range(K_p):
            idx1 = 2 * h
            idx2 = 2 * h + 1

            # N_p が奇数の場合、最後の d_{N_p} は d_1 とペアリング
            if idx2 >= N_p:
                idx2 = 0

            ext_addr = ExtensionNodeAddress(weight=p, index=h)
            ext_node = ExtensionNode(
                address=ext_addr,
                input_1=addrs[idx1],
                input_2=addrs[idx2],
                mixer_size=2,
                droplet_weight=p,
            )
            extension_nodes.append(ext_node)

    return extension_nodes


def describe_extension_nodes(extension_nodes: List[ExtensionNode]) -> str:
    """拡張ノードの一覧を人間可読な文字列で返す（デバッグ・ログ用）"""
    if not extension_nodes:
        return "  (拡張ノードなし)"
    lines = []
    for ext in extension_nodes:
        a = ext.address
        i1, i2 = ext.input_1, ext.input_2
        lines.append(
            f"  u_({a.weight},{a.index}): "
            f"({i1.target_id},{i1.level},{i1.index}) x ({i2.target_id},{i2.level},{i2.index})"
        )
    return "\n".join(lines)
