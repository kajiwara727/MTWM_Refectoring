import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.patches as mpatches
from core.solver.problem import MTWMProblem
from .base_visualizer import BaseVisualizer

class MTWMProblemVisualizer(BaseVisualizer):
    def __init__(self, problem: MTWMProblem, config=None):
        super().__init__(config if config else __import__('visualization.config').config.VisualizerConfig)
        self._build_graph(problem)

    def _build_graph(self, problem: MTWMProblem) -> None:
        nodes_metadata = problem.nodes_metadata
        for idx, data in nodes_metadata.items():
            m, l, k = idx
            self.G.add_node(idx, **data)
            self.pos[idx] = (m * self.config.X_SPACING_TARGET + k * self.config.X_SPACING_NODE, -l)

        for dst_idx, sources in problem.potential_sources_map.items():
            for src_idx in sources:
                dst_node_obj = nodes_metadata[dst_idx]['obj']
                m_dst, m_src = dst_idx[0], src_idx[0]
                
                is_default_edge = (m_src == m_dst) and any(child.id == (src_idx[1], src_idx[2]) for child in dst_node_obj.children)
                color, edge_type = ('black', 'default') if is_default_edge else ('red', 'potential')
                self.G.add_edge(src_idx, dst_idx, edge_type=edge_type, color=color, weight=1.5 if is_default_edge else 1.0)

    def draw(self, output_path: str, title: str = "MTWM Initial Problem Structure", show: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(14, 9))
        
        node_colors = ["lightgreen" if d.get('is_leaf') else "skyblue" for _, d in self.G.nodes(data=True)]
        labels = {n: f"ID:({n[0]},{n[1]},{n[2]})\nP:{d.get('p_value', '-')}" for n, d in self.G.nodes(data=True)}

        nx.draw_networkx_nodes(self.G, self.pos, ax=ax, node_color=node_colors, node_size=self.config.NODE_SIZE, edgecolors="black")
        nx.draw_networkx_labels(self.G, self.pos, ax=ax, labels=labels, font_size=self.config.FONT_SIZE)

        default_edges = [(u, v) for u, v, d in self.G.edges(data=True) if d['edge_type'] == 'default']
        potential_edges = [(u, v) for u, v, d in self.G.edges(data=True) if d['edge_type'] == 'potential']

        if default_edges:
            nx.draw_networkx_edges(self.G, self.pos, ax=ax, edgelist=default_edges, edge_color='black', width=1.5, arrows=True, arrowsize=self.config.ARROW_SIZE)
        if potential_edges:
            nx.draw_networkx_edges(self.G, self.pos, ax=ax, edgelist=potential_edges, edge_color='red', width=1.0, arrows=True, arrowsize=self.config.ARROW_SIZE, connectionstyle="arc3,rad=0.2")

        self._draw_background_levels(ax)
        
        handles = [mpatches.Patch(color='black', label='Default Connection'), mpatches.Patch(color='red', label='Potential Connection (Sharing)')]
        ax.legend(handles=handles, loc='upper left')
        
        plt.title(title, fontsize=14)
        self._save_and_close(fig, output_path, show)