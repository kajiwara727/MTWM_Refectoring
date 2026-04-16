import itertools
from typing import List, Dict, Tuple, Optional
from core.models import Target, MixingNode

class MTWMProblem:
    def __init__(self, targets: List[Target], tree_structures: List[Dict[Tuple[int, int], MixingNode]]):
        """
        Args:
            targets: Targetデータクラスのリスト
            tree_structures: 各ターゲットのノード辞書 [(level, k) -> MixingNode] のリスト
        """
        self.targets = targets
        self.num_reagents = len(targets[0].ratios) if targets else 0
        self.tree_structures = tree_structures
        
        # 1. 基本となるノード情報の整理
        self.nodes_metadata = self._build_nodes_metadata()
        
        # 2. 潜在的な接続（エッジ）候補の計算 (MAX_LEVEL_DIFFは削除)
        self.potential_sources_map = self._precompute_potential_sources()
        
        # 3. 各ノードが必要とする変数インデックスを定義
        self._assign_variable_indices()

    def _build_nodes_metadata(self):
        """全ターゲットのノードをフラットな辞書で管理"""
        nodes = {}
        for m, tree in enumerate(self.tree_structures):
            for (l, k), node_obj in tree.items():
                nodes[(m, l, k)] = {
                    'obj': node_obj,
                    'is_leaf': l == 0,
                    # ここに具体的な数値を保持（最適化計算で定数として使用）
                    'p_value': node_obj.p_value,
                    'factor': self.targets[m].factors[l]
                }
        return nodes

    def _precompute_potential_sources(self) -> Dict[Tuple, List[Tuple]]:
        """
        濃度整合性と物理制約を満たす接続候補を計算。
        MAX_LEVEL_DIFF による制限は行わない。
        """
        source_map = {}
        all_indices = list(self.nodes_metadata.keys())

        for dst_idx, src_idx in itertools.product(all_indices, repeat=2):
            m_dst, l_dst, k_dst = dst_idx
            m_src, l_src, k_src = src_idx

            # 1. 物理的制約: 送信元は送信先より高いレベル（l）である必要がある
            if l_src <= l_dst:
                continue

            # 2. 濃度整合性チェック
            meta_dst = self.nodes_metadata[dst_idx]
            meta_src = self.nodes_metadata[src_idx]
            
            # (P_dst / f_dst) が P_src で割り切れる場合のみ接続可能
            if (meta_dst['p_value'] // meta_dst['factor']) % meta_src['p_value'] != 0:
                continue

            # 3. 親子関係（デフォルトエッジ）の判定
            # デフォルトエッジは無条件で候補に入れる（上記濃度チェックは通るはず）
            
            if dst_idx not in source_map:
                source_map[dst_idx] = []
            source_map[dst_idx].append(src_idx)
            
        return source_map

    def _assign_variable_indices(self):
        """
        各ノードに対し、数式モデルで使用する変数の「キー（インデックス）」を割り当てる。
        実際の変数生成（LpVariable等）はソルバー担当者がこのキーを元に行う。
        """
        for idx, data in self.nodes_metadata.items():
            m, l, k = idx
            
            # 濃度変数 R[m, l, k, reagent_t]
            data['var_keys_R'] = [(m, l, k, t) for t in range(self.num_reagents)]
            
            # 試薬注入量 r[m, l, k, reagent_t]
            data['var_keys_r'] = [(m, l, k, t) for t in range(self.num_reagents)]
            
            # 合計注入量
            data['var_key_total_input'] = (m, l, k)
            
            # 廃棄量 (Leaf以外)
            if not data['is_leaf']:
                data['var_key_waste'] = (m, l, k)
            
            # Sharing（接続）変数
            # intra_sharing[src_idx, dst_idx], inter_sharing[src_idx, dst_idx]
            data['potential_src_indices'] = self.potential_sources_map.get(idx, [])

    def get_node_data(self, m, l, k):
        return self.nodes_metadata.get((m, l, k))