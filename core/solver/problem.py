import itertools
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from core.models import Target, MixingNode, NodeAddress

@dataclass
class NodeOptimizationMetadata:
    """数理最適化モデル構築に必要なノードのメタデータ"""
    obj: MixingNode
    is_leaf: bool
    droplet_weight: int
    factor: int
    
    # ソルバー側の変数キー（Or-Toolsで変数を生成する際の識別用）
    # 変数キー自体は文字列などで構築しやすくするためタプルや識別子を保持するリストなどにするか、
    # ここではシンプルに生成予定のリストを保持する
    var_keys_R: List[Tuple] = field(default_factory=list)
    var_keys_r: List[Tuple] = field(default_factory=list)
    var_key_total_input: Optional[Tuple] = None
    var_key_waste: Optional[Tuple] = None
    potential_src_addresses: List[NodeAddress] = field(default_factory=list)

class MTWMProblem:
    def __init__(self, targets: List[Target], tree_structures: List[Dict[NodeAddress, MixingNode]]):
        """
        Args:
            targets: Targetデータクラスのリスト
            tree_structures: 各ターゲットのノード辞書 [NodeAddress -> MixingNode] のリスト
        """
        self.targets = targets
        self.num_reagents = len(targets[0].ratios) if targets else 0
        self.tree_structures = tree_structures
        
        # 1. 基本となるノード情報の整理 (dictから型安全なメタデータクラスの辞書へ)
        self.nodes_metadata: Dict[NodeAddress, NodeOptimizationMetadata] = self._build_nodes_metadata()
        
        # 2. 潜在的な接続（エッジ）候補の計算
        self.potential_sources_map: Dict[NodeAddress, List[NodeAddress]] = self._precompute_potential_sources()
        
        # 3. 各ノードが必要とする変数インデックスを定義
        self._assign_variable_indices()

    def _build_nodes_metadata(self) -> Dict[NodeAddress, NodeOptimizationMetadata]:
        """全ターゲットのノードをフラットな辞書で管理"""
        nodes = {}
        for tree in self.tree_structures:
            for address, node_obj in tree.items():
                nodes[address] = NodeOptimizationMetadata(
                    obj=node_obj,
                    is_leaf=(address.level == 0),
                    droplet_weight=node_obj.droplet_weight,
                    factor=node_obj.mixer_size
                )
        return nodes

    def _precompute_potential_sources(self) -> Dict[NodeAddress, List[NodeAddress]]:
        """濃度整合性と物理制約を満たす接続候補を計算"""
        source_map = {}
        all_addresses = list(self.nodes_metadata.keys())

        for dst_addr, src_addr in itertools.product(all_addresses, repeat=2):
            # 1. 物理的制約: 送信元は送信先より高いレベルである必要がある
            if src_addr.level <= dst_addr.level:
                continue

            meta_dst = self.nodes_metadata[dst_addr]
            meta_src = self.nodes_metadata[src_addr]

            # 親子関係（デフォルトエッジ）の判定
            is_default = False
            if src_addr.target_id == dst_addr.target_id:
                is_default = any(child.address == src_addr for child in meta_dst.obj.children)
            
            # 2. 濃度整合性チェック
            # (P_dst / f_dst) が P_src で割り切れる場合のみ接続可能
            if not is_default:
                dst_val = meta_dst.droplet_weight // meta_dst.factor
                if dst_val % meta_src.droplet_weight != 0:
                    continue

            if dst_addr not in source_map:
                source_map[dst_addr] = []
            source_map[dst_addr].append(src_addr)
            
        return source_map

    def _assign_variable_indices(self):
        """数式モデルで使用する変数の「キー（インデックス）」を割り当てる"""
        for address, data in self.nodes_metadata.items():
            m, l, k = address.target_id, address.level, address.index
            
            # 濃度変数 R, 試薬注入量 r
            data.var_keys_R = [(m, l, k, t) for t in range(self.num_reagents)]
            data.var_keys_r = [(m, l, k, t) for t in range(self.num_reagents)]
            data.var_key_total_input = (m, l, k)
            
            if not data.is_leaf:
                data.var_key_waste = (m, l, k)
            
            data.potential_src_addresses = self.potential_sources_map.get(address, [])

    def get_node_data(self, address: NodeAddress) -> Optional[NodeOptimizationMetadata]:
        return self.nodes_metadata.get(address)