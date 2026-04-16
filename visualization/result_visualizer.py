import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from typing import Dict, Any
from .base_visualizer import BaseVisualizer

class MTWMResultVisualizer(BaseVisualizer):
    def __init__(self, solution_data: Dict[str, Any], config=None):
        super().__init__(config if config else __import__('visualization.config').config.VisualizerConfig)
        self.solution = solution_data
        self._build_graph(self.solution)

    def _build_graph(self, solution: Dict[str, Any]) -> None:
        for node in solution.get("nodes", []):
            node_id = node["id"]
            self.G.add_node(node_id, node_type='mixing', **node)
            m, l, k = node_id
            self.pos[node_id] = (m * self.config.X_SPACING_TARGET + k * self.config.X_SPACING_NODE, -l)

        for node in solution.get("nodes", []):
            mixing_id = node["id"]
            for t_idx, vol in enumerate(node.get('r', [])):
                if vol > 0:
                    reagent_id = (mixing_id, f"reagent_t{t_idx}")
                    self.G.add_node(reagent_id, node_type='reagent', label=f"t{t_idx}", volume=vol)
                    mx, my = self.pos[mixing_id]
                    self.pos[reagent_id] = (mx + (t_idx * 0.4 - 0.2), my + self.config.Y_OFFSET_REAGENT)
                    self.G.add_edge(reagent_id, mixing_id, volume=vol, edge_type='reagent')

        for edge in solution.get("edges", []):
            src, dst, vol = edge["source"], edge["target"], edge["volume"]
            is_intra = (src[0] == dst[0])
            self.G.add_edge(src, dst, volume=vol, edge_type='tree', is_intra=is_intra)

    def draw(self, output_path: str, title: str = "MTWM Optimized Result", show: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(18, 12))
        
        mixing_nodes = [n for n, d in self.G.nodes(data=True) if d.get('node_type') == 'mixing']
        reagent_nodes = [n for n, d in self.G.nodes(data=True) if d.get('node_type') == 'reagent']

        all_volumes = [d['volume'] for _, _, d in self.G.edges(data=True)] or [0]
        min_v, max_v = min(all_volumes), max(all_volumes)
        if min_v == max_v:
            min_v, max_v = 0, max_v + 1
            
        norm = mcolors.Normalize(vmin=min_v, vmax=max_v)
        scalar_map = cm.ScalarMappable(norm=norm, cmap=self.config.VOLUME_CMAP)

        # Mixing Nodes
        nx.draw_networkx_nodes(self.G, self.pos, nodelist=mixing_nodes, node_color="white", node_size=self.config.RESULT_NODE_SIZE, edgecolors="black", ax=ax)
        nx.draw_networkx_labels(self.G, self.pos, labels={n: f"ID:({n[0]},{n[1]},{n[2]})\nIn:{self.G.nodes[n]['total_input']}" for n in mixing_nodes}, font_size=self.config.FONT_SIZE, ax=ax)

        for n in mixing_nodes:
            x, y = self.pos[n]
            ax.text(x, y + self.config.Y_OFFSET_STATE, f"State: {self.G.nodes[n].get('R', [])}", 
                    fontsize=self.config.STATE_FONT_SIZE, ha='center', fontweight='bold', 
                    bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray', boxstyle='round,pad=0.2'))

        # Reagent Nodes
        nx.draw_networkx_nodes(self.G, self.pos, nodelist=reagent_nodes, node_shape='s', node_color="orange", node_size=self.config.REAGENT_NODE_SIZE, ax=ax)
        nx.draw_networkx_labels(self.G, self.pos, labels={n: self.G.nodes[n]['label'] for n in reagent_nodes}, font_size=self.config.FONT_SIZE, ax=ax)

        # Edges
        for u, v, d in self.G.edges(data=True):
            vol = d['volume']
            edge_color = scalar_map.to_rgba(vol)
            width = 1.5 + (vol * 1.5)
            style = 'solid' if d.get('is_intra', True) else 'dashed'
            rad = 0.1 if d['edge_type'] == 'tree' else 0.0
            nx.draw_networkx_edges(self.G, self.pos, edgelist=[(u, v)], width=width, edge_color=[edge_color], style=style, arrows=True, arrowsize=20, connectionstyle=f"arc3,rad={rad}", ax=ax)

        cbar = fig.colorbar(scalar_map, ax=ax, shrink=0.5, pad=0.05)
        cbar.set_label('Droplet Volume (Flow)', fontsize=10, fontweight='bold')

        self._draw_background_levels(ax)
        
        plt.title(f"{title}\nTotal waste fluids: {self.solution.get('total_waste_fluids', 0)}", fontsize=16)
        plt.axis('off')
        self._save_and_close(fig, output_path, show)