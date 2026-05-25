# core/solver/extension_problem.py
"""
【提案手法】拡張ノードを組み込んだ問題クラス（論文 Section III）

MTWMProblem を継承し、以下を追加:
  - ExtensionNode のリスト（generate_extension_nodes で生成）
  - extension_sources_map: 各宛先ノードへの有効な拡張ノード候補
  - extension_input_map:   各通常ノードを入力とする拡張ノード候補
"""

from dataclasses import dataclass, field
from typing import List, Dict

from core.models import NodeAddress, ExtensionNode, ExtensionNodeAddress, Target, MixingNode
from core.algorithm.extension import generate_extension_nodes, describe_extension_nodes
from .problem import MTWMProblem


class ExtensionMTWMProblem(MTWMProblem):
    """
    拡張ノードを組み込んだ MTWM 問題クラス。

    追加属性:
        max_mixer_size (int): 最大ミキサーサイズ M
        extension_nodes (List[ExtensionNode]): 生成された拡張ノードのリスト
        extension_sources_map (Dict[NodeAddress, List[ExtensionNodeAddress]]):
            各宛先ノードが利用できる拡張ノードの候補
        extension_input_map (Dict[NodeAddress, List[ExtensionNodeAddress]]):
            各通常ノードを「入力」とする拡張ノードの一覧
    """

    def __init__(
        self,
        targets: List[Target],
        tree_structures: List[Dict[NodeAddress, MixingNode]],
        max_mixer_size: int,
    ):
        self.max_mixer_size = max_mixer_size
        # 親クラスの初期化（potential_sources_map などを構築）
        super().__init__(targets, tree_structures)

        # 拡張ノードの生成
        self.extension_nodes: List[ExtensionNode] = generate_extension_nodes(
            tree_structures, max_mixer_size
        )

        # 拡張ノードを宛先ノードにマッピング
        self.extension_sources_map: Dict[NodeAddress, List[ExtensionNodeAddress]] = \
            self._precompute_extension_sources()

        # 通常ノードを入力とする拡張ノードの逆引きマップ
        self.extension_input_map: Dict[NodeAddress, List[ExtensionNodeAddress]] = \
            self._build_extension_input_map()

        # デバッグ用ログ
        print(f"[ExtensionProblem] 拡張ノード数: {len(self.extension_nodes)}")
        if self.extension_nodes:
            print(describe_extension_nodes(self.extension_nodes))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _precompute_extension_sources(self) -> Dict[NodeAddress, List[ExtensionNodeAddress]]:
        """
        各宛先ノード v^m_{l,i} に対して、利用可能な拡張ノード u_{p,h} を列挙する。

        利用条件（論文 式 (2) の拡張）:
          1. 重み整合性: (P_dst / f_dst) mod p == 0
          2. レベル条件: 宛先のレベル < 拡張ノードの入力ノードの最小レベル
             （液滴は常に根方向にしか流れないため）
        """
        ext_map: Dict[NodeAddress, List[ExtensionNodeAddress]] = {}

        for dst_addr, meta_dst in self.nodes_metadata.items():
            p_dst = meta_dst.droplet_weight
            f_dst = meta_dst.factor

            # level == 0（ターゲットノード）は除外しない
            # → ターゲット直前の混合ステップにも拡張ノードを適用できる

            valid_exts = []
            for ext_node in self.extension_nodes:
                p = ext_node.address.weight

                # 条件1: 重み整合性 (P_dst / f_dst) mod p == 0
                if (p_dst // f_dst) % p != 0:
                    continue

                # 条件2: レベル条件（循環を防ぐ）
                min_input_level = min(ext_node.input_1.level, ext_node.input_2.level)
                if dst_addr.level >= min_input_level:
                    continue

                valid_exts.append(ext_node.address)

            if valid_exts:
                ext_map[dst_addr] = valid_exts

        return ext_map

    def _build_extension_input_map(self) -> Dict[NodeAddress, List[ExtensionNodeAddress]]:
        """
        各通常ノード addr が「入力」として使われる拡張ノードをリストアップする。
        ソルバーでの total_used 計算（廃棄液滴の算出）に利用する。
        """
        input_map: Dict[NodeAddress, List[ExtensionNodeAddress]] = {}

        for ext_node in self.extension_nodes:
            for input_addr in (ext_node.input_1, ext_node.input_2):
                if input_addr not in input_map:
                    input_map[input_addr] = []
                input_map[input_addr].append(ext_node.address)

        return input_map
