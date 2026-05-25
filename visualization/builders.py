import networkx as nx
from typing import Dict
from core.models import NodeAddress, MixingNode, ExtensionNodeAddress
from core.solver.problem import MTWMProblem
from core.solver.dto import OptimizationResult
from .config import VisualizerConfig

class BaseGraphBuilder:
    def __init__(self, config: type = VisualizerConfig):
        self.config = config
        self.G = nx.DiGraph()
        self.pos = {}

    def _calculate_position(self, address: NodeAddress, is_single_target: bool = False) -> tuple[float, float]:
        x_target_offset = 0 if is_single_target else address.target_id * self.config.X_SPACING_TARGET
        x_pos = x_target_offset + address.index * self.config.X_SPACING_NODE
        return (x_pos, -address.level)

class DFMMGraphBuilder(BaseGraphBuilder):
    def build(self, tree_nodes: Dict[NodeAddress, MixingNode]):
        for address, node_obj in tree_nodes.items():
            self.G.add_node(address, obj=node_obj, is_leaf=(address.level == 0), droplet_weight=node_obj.droplet_weight)
            self.pos[address] = self._calculate_position(address, is_single_target=True)
            for child in node_obj.children:
                self.G.add_edge(child.address, address, edge_type='default', color='black', weight=1.5)
        return self.G, self.pos

class MTWMProblemGraphBuilder(BaseGraphBuilder):
    def build(self, problem: MTWMProblem):
        for address, meta in problem.nodes_metadata.items():
            self.G.add_node(address, obj=meta.obj, is_leaf=meta.is_leaf, droplet_weight=meta.droplet_weight)
            self.pos[address] = self._calculate_position(address)

        for dst_addr, sources in problem.potential_sources_map.items():
            for src_addr in sources:
                dst_node_obj = problem.nodes_metadata[dst_addr].obj
                is_default_edge = (src_addr.target_id == dst_addr.target_id) and any(child.address == src_addr for child in dst_node_obj.children)
                color, edge_type = ('black', 'default') if is_default_edge else ('red', 'potential')
                self.G.add_edge(src_addr, dst_addr, edge_type=edge_type, color=color, weight=1.5 if is_default_edge else 1.0)
        return self.G, self.pos

class MTWMResultGraphBuilder(BaseGraphBuilder):
    def build(self, solution: OptimizationResult):
        for node in solution.nodes:
            address = node.address
            self.G.add_node(address, node_type='mixing', node_res=node)
            self.pos[address] = self._calculate_position(address)

        for node in solution.nodes:
            mixing_addr = node.address
            for t_idx, vol in enumerate(node.injected_reagent_volumes):
                if vol > 0:
                    reagent_id = (mixing_addr, f"reagent_t{t_idx}")
                    self.G.add_node(reagent_id, node_type='reagent', label=f"t{t_idx}", volume=vol)
                    mx, my = self.pos[mixing_addr]
                    self.pos[reagent_id] = (mx + (t_idx * 0.4 - 0.2), my + self.config.Y_OFFSET_REAGENT)
                    self.G.add_edge(reagent_id, mixing_addr, volume=vol, edge_type='reagent')

        for edge in solution.edges:
            src, dst, vol = edge.source, edge.target, edge.volume
            is_intra = (src.target_id == dst.target_id)
            self.G.add_edge(src, dst, volume=vol, edge_type='tree', is_intra=is_intra)
        return self.G, self.pos

class ProposedHeuristicGraphBuilder(BaseGraphBuilder):
    def build(self, problem):
        # 提案手法の問題クラス (ProposedMTWMProblem) からメタデータを取得
        for address, meta in problem.nodes_metadata.items():
            # meta.dominant_reagents をノードのデータとして保持
            self.G.add_node(
                address, 
                obj=meta.obj, 
                is_leaf=meta.is_leaf, 
                droplet_weight=meta.droplet_weight,
                dominant_reagents=getattr(meta, 'dominant_reagents', set())
            )
            self.pos[address] = self._calculate_position(address)

        # 許可された接続候補だけをエッジとして追加
        for dst_addr, sources in problem.potential_sources_map.items():
            for src_addr in sources:
                dst_node_obj = problem.nodes_metadata[dst_addr].obj
                is_default_edge = (src_addr.target_id == dst_addr.target_id) and any(child.address == src_addr for child in dst_node_obj.children)
                color, edge_type = ('black', 'default') if is_default_edge else ('blue', 'heuristic_potential')
                self.G.add_edge(src_addr, dst_addr, edge_type=edge_type, color=color, weight=1.5 if is_default_edge else 1.0)

        return self.G, self.pos


# ============================================================
# 【提案手法】拡張ノード問題グラフビルダー
# ============================================================

class ExtensionProblemGraphBuilder(BaseGraphBuilder):
    """
    拡張ノードの候補接続（z エッジ）も含めた問題グラフを構築する。
    通常ノード（丸）と拡張ノード（六角形相当）を別色で区別する。
    """

    def build(self, problem) -> tuple:
        # --- 通常ノード ---
        for address, meta in problem.nodes_metadata.items():
            self.G.add_node(
                address,
                node_kind="regular",
                obj=meta.obj,
                is_leaf=meta.is_leaf,
                droplet_weight=meta.droplet_weight,
            )
            self.pos[address] = self._calculate_position(address)

        # --- 通常ノード間のエッジ ---
        for dst_addr, sources in problem.potential_sources_map.items():
            for src_addr in sources:
                dst_obj = problem.nodes_metadata[dst_addr].obj
                is_default = (src_addr.target_id == dst_addr.target_id) and any(
                    child.address == src_addr for child in dst_obj.children
                )
                color = "black" if is_default else "red"
                etype = "default" if is_default else "potential"
                self.G.add_edge(src_addr, dst_addr, edge_type=etype, color=color, weight=1.5 if is_default else 1.0)

        # --- 拡張ノード ---
        for ext_node in problem.extension_nodes:
            ext_addr = ext_node.address
            p, h = ext_addr.weight, ext_addr.index
            # Y 座標は入力ノードの中間、X 座標はずらして表示
            in1_pos = self.pos.get(ext_node.input_1, (0, 0))
            in2_pos = self.pos.get(ext_node.input_2, (0, 0))
            x = (in1_pos[0] + in2_pos[0]) / 2 + 0.3 * h
            y = (in1_pos[1] + in2_pos[1]) / 2 - 0.5
            self.G.add_node(
                ext_addr,
                node_kind="extension",
                droplet_weight=p,
                label=f"u_({p},{h})",
            )
            self.pos[ext_addr] = (x, y)

            # 入力エッジ（input_1, input_2 → extension node）
            self.G.add_edge(ext_node.input_1, ext_addr, edge_type="ext_input", color="purple", weight=1.2)
            self.G.add_edge(ext_node.input_2, ext_addr, edge_type="ext_input", color="purple", weight=1.2)

        # --- 拡張ノード → 宛先ノードのエッジ候補（z） ---
        for dst_addr, ext_addrs in problem.extension_sources_map.items():
            for ext_addr in ext_addrs:
                self.G.add_edge(ext_addr, dst_addr, edge_type="ext_potential", color="orange", weight=0.8)

        return self.G, self.pos


class ExtensionResultGraphBuilder(BaseGraphBuilder):
    """
    最適化結果グラフ（通常エッジ w + 拡張エッジ z + 拡張ノード）を構築する。
    """

    def build(self, data: dict) -> tuple:
        solution = data["solution"]
        problem = data.get("problem")

        # --- 通常ノード（アクティブなもの）---
        for node_res in solution.nodes:
            address = node_res.address
            self.G.add_node(address, node_kind="regular", node_res=node_res)
            self.pos[address] = self._calculate_position(address)

        # --- アクティブな拡張ノード ---
        for ext_res in solution.extension_nodes:
            ext_addr = ext_res.address
            in1_pos = self.pos.get(ext_res.input_1, (0, 0))
            in2_pos = self.pos.get(ext_res.input_2, (0, 0))
            x = (in1_pos[0] + in2_pos[0]) / 2
            y = (in1_pos[1] + in2_pos[1]) / 2 - 0.5
            self.G.add_node(
                ext_addr,
                node_kind="extension",
                ext_res=ext_res,
                label=f"u_({ext_addr.weight},{ext_addr.index})\n{ext_res.concentration_state}",
            )
            self.pos[ext_addr] = (x, y)

        # --- 試薬注入ノード（リーフ相当）---
        for node_res in solution.nodes:
            mixing_addr = node_res.address
            for t_idx, vol in enumerate(node_res.injected_reagent_volumes):
                if vol > 0:
                    reagent_id = (mixing_addr, f"reagent_t{t_idx}")
                    self.G.add_node(reagent_id, node_kind="reagent", label=f"t{t_idx}", volume=vol)
                    mx, my = self.pos[mixing_addr]
                    self.pos[reagent_id] = (mx + (t_idx * 0.4 - 0.2), my + 0.8)
                    self.G.add_edge(reagent_id, mixing_addr, volume=vol, edge_type="reagent")

        # --- 通常エッジ（w）と拡張エッジ（z）---
        for edge in solution.edges:
            src, dst, vol = edge.source, edge.target, edge.volume
            if isinstance(src, ExtensionNodeAddress):
                etype = "extension"
                is_intra = False
            else:
                etype = "tree"
                is_intra = (src.target_id == dst.target_id)  # type: ignore[union-attr]
            self.G.add_edge(src, dst, volume=vol, edge_type=etype, is_intra=is_intra)

        return self.G, self.pos