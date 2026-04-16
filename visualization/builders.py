import networkx as nx
from typing import Dict
from core.models import NodeAddress, MixingNode
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