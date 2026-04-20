import itertools
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict

from core.models import NodeAddress
from .problem import MTWMProblem, NodeOptimizationMetadata

@dataclass
class ProposedNodeMetadata(NodeOptimizationMetadata):
    """提案手法用に最多試薬情報を追加したメタデータ"""
    dominant_reagents: set = field(default_factory=set)

class ProposedMTWMProblem(MTWMProblem):
    """提案手法（DFMMの仮割り当てを利用した経路削減）用の問題クラス"""
    
    def _build_nodes_metadata(self) -> Dict[NodeAddress, ProposedNodeMetadata]:
        nodes = {}
        for tree in self.tree_structures:
            for address, node_obj in tree.items():
                
                # DFMMの仮割り当てから、最も多い試薬を計算
                valid_reagents = [r for r in node_obj.reagent_dispensations if r != -1]
                dominant_reagents = set()
                if valid_reagents:
                    counts = Counter(valid_reagents)
                    max_count = max(counts.values())
                    dominant_reagents = {r for r, count in counts.items() if count == max_count}
                
                nodes[address] = ProposedNodeMetadata(
                    obj=node_obj,
                    is_leaf=(address.level == 0),
                    droplet_weight=node_obj.droplet_weight,
                    factor=node_obj.mixer_size,
                    dominant_reagents=dominant_reagents
                )
        return nodes

    def _precompute_potential_sources(self) -> Dict[NodeAddress, List[NodeAddress]]:
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
            
            # 親子関係以外の潜在エッジに対するフィルタリング
            if not is_default:
                # 2. 濃度整合性チェック
                dst_val = meta_dst.droplet_weight // meta_dst.factor
                if dst_val % meta_src.droplet_weight != 0:
                    continue
                
                # 3. 提案手法: 最多試薬の一致チェック
                src_dominants = meta_src.dominant_reagents
                dst_dominants = meta_dst.dominant_reagents
                
                # 送信元・送信先の両方に仮試薬が割り当てられている場合のみ判定
                if src_dominants and dst_dominants:
                    # 共通の最多試薬が1つも無い場合は、接続候補から除外
                    if not src_dominants.intersection(dst_dominants):
                        continue

            if dst_addr not in source_map:
                source_map[dst_addr] = []
            source_map[dst_addr].append(src_addr)
            
        return source_map