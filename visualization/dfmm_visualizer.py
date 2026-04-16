# visualization/dfmm_visualizer.py
import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.patches as mpatches
from typing import Dict, Any
from core.models import MixingNode, NodeAddress
from .base_visualizer import BaseVisualizer

class DFMMVisualizer(BaseVisualizer):
    def __init__(self, tree_nodes: Dict[NodeAddress, MixingNode], config=None):
        super().__init__(config if config else __import__('visualization.config').config.VisualizerConfig)
        self._build_graph(tree_nodes)

    def _build_graph(self, tree_nodes: Dict[NodeAddress, MixingNode]) -> None:
        for address, node_obj in tree_nodes.items():
            self.G.add_node(address, obj=node_obj, is_leaf=(address.level == 0), droplet_weight=node_obj.droplet_weight)
            self.pos[address] = self._calculate_position(address, is_single_target=True)
            
            for child in node_obj.children:
                self.G.add_edge(child.address, address, edge_type='default', color='black', weight=1.5)

    def _get_node_label(self, node_data: Dict[str, Any]) -> str:
        node_obj = node_data.get('obj')
        if not node_obj: return "Unknown"
        
        label_parts = [
            f"ID:({node_obj.address.level},{node_obj.address.index})", 
            f"P:{node_data.get('droplet_weight', '-')}"
        ]
        if node_obj.reagent_dispensations:
            label_parts.append(f"Reagents:\n{node_obj.reagent_dispensations}")
            
        return "\n".join(label_parts)

    def draw(self, output_path: str, title: str = "DFMM Routing Tree", show: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        node_colors = ["lightgreen" if d.get('is_leaf') else "skyblue" for _, d in self.G.nodes(data=True)]
        labels = {n: self._get_node_label(d) for n, d in self.G.nodes(data=True)}

        nx.draw_networkx_nodes(self.G, self.pos, ax=ax, node_color=node_colors, node_size=self.config.NODE_SIZE, edgecolors="black")
        nx.draw_networkx_labels(self.G, self.pos, ax=ax, labels=labels, font_size=self.config.FONT_SIZE)

        edges = list(self.G.edges(data=True))
        if edges:
            nx.draw_networkx_edges(self.G, self.pos, ax=ax, edgelist=[(u, v) for u, v, _ in edges], 
                                   edge_color='black', width=1.5, arrows=True, arrowsize=self.config.ARROW_SIZE)

        self._draw_background_levels(ax)
        
        handles = [mpatches.Patch(color='black', label='Default Connection')]
        ax.legend(handles=handles, loc='upper left')
        
        plt.title(title, fontsize=14)
        self._save_and_close(fig, output_path, show)