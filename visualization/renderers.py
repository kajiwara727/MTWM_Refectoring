import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from typing import Dict, Any

class BaseRenderer:
    def __init__(self, G: nx.DiGraph, pos: dict, config):
        self.G = G
        self.pos = pos
        self.config = config

    def _draw_background_levels(self, ax: plt.Axes) -> None:
        if not self.pos: return
        x_vals = [x for x, y in self.pos.values() if isinstance(x, (int, float))]
        if not x_vals: return
        x_min, x_max = min(x_vals) - 1, max(x_vals) + 2
        y_levels = sorted(list(set(y for x, y in self.pos.values() if isinstance(y, (int, float)) and y <= 0 and y == int(y))), reverse=True)
        for y_coord in y_levels:
            ax.hlines(y_coord, x_min, x_max, colors="gray", linestyles="dashed", alpha=0.5, zorder=0)
            level_num = int(-y_coord)
            ax.text(x_max, y_coord, f"Level {level_num}", color='coral', fontsize=12, fontweight='bold', va='center')

    def _save_and_close(self, fig: plt.Figure, output_path: str, show: bool) -> None:
        plt.savefig(output_path, bbox_inches='tight')
        if show: plt.show()
        plt.close(fig)


class DFMMRenderer(BaseRenderer):
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

    def render(self, output_path: str, title: str, show: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(12, 8))
        node_colors = ["lightgreen" if d.get('is_leaf') else "skyblue" for _, d in self.G.nodes(data=True)]
        labels = {n: self._get_node_label(d) for n, d in self.G.nodes(data=True)}

        nx.draw_networkx_nodes(self.G, self.pos, ax=ax, node_color=node_colors, node_size=self.config.NODE_SIZE, edgecolors="black")
        nx.draw_networkx_labels(self.G, self.pos, ax=ax, labels=labels, font_size=self.config.FONT_SIZE)

        edges = list(self.G.edges(data=True))
        if edges:
            nx.draw_networkx_edges(self.G, self.pos, ax=ax, edgelist=[(u, v) for u, v, _ in edges], edge_color='black', width=1.5, arrows=True, arrowsize=self.config.ARROW_SIZE)

        self._draw_background_levels(ax)
        handles = [mpatches.Patch(color='black', label='Default Connection')]
        ax.legend(handles=handles, loc='upper left')
        plt.title(title, fontsize=14)
        self._save_and_close(fig, output_path, show)


class MTWMProblemRenderer(BaseRenderer):
    def render(self, output_path: str, title: str, show: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(14, 9))
        node_colors = ["lightgreen" if d.get('is_leaf') else "skyblue" for _, d in self.G.nodes(data=True)]
        labels = {n: f"ID:({n.target_id},{n.level},{n.index})\nP:{d.get('droplet_weight', '-')}" for n, d in self.G.nodes(data=True)}

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


class MTWMResultRenderer(BaseRenderer):
    def render(self, output_path: str, title: str, total_waste: int = 0, show: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(18, 12))
        mixing_nodes = [n for n, d in self.G.nodes(data=True) if d.get('node_type') == 'mixing']
        reagent_nodes = [n for n, d in self.G.nodes(data=True) if d.get('node_type') == 'reagent']

        all_volumes = [d['volume'] for _, _, d in self.G.edges(data=True)] or [0]
        min_v, max_v = min(all_volumes), max(all_volumes)
        if min_v == max_v: min_v, max_v = 0, max_v + 1
        
        norm = mcolors.Normalize(vmin=min_v, vmax=max_v)
        scalar_map = cm.ScalarMappable(norm=norm, cmap=self.config.VOLUME_CMAP)

        nx.draw_networkx_nodes(self.G, self.pos, nodelist=mixing_nodes, node_color="white", node_size=self.config.RESULT_NODE_SIZE, edgecolors="black", ax=ax)
        labels = {n: f"ID:({n.target_id},{n.level},{n.index})\nIn:{self.G.nodes[n]['node_res'].total_input}" for n in mixing_nodes}
        nx.draw_networkx_labels(self.G, self.pos, labels=labels, font_size=self.config.FONT_SIZE, ax=ax)

        for n in mixing_nodes:
            x, y = self.pos[n]
            state = self.G.nodes[n]['node_res'].concentration_state
            ax.text(x, y + self.config.Y_OFFSET_STATE, f"State: {state}", fontsize=self.config.STATE_FONT_SIZE, ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray', boxstyle='round,pad=0.2'))

        nx.draw_networkx_nodes(self.G, self.pos, nodelist=reagent_nodes, node_shape='s', node_color="orange", node_size=self.config.REAGENT_NODE_SIZE, ax=ax)
        nx.draw_networkx_labels(self.G, self.pos, labels={n: self.G.nodes[n]['label'] for n in reagent_nodes}, font_size=self.config.FONT_SIZE, ax=ax)

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
        plt.title(f"Total waste fluids: {total_waste}", fontsize=16)
        plt.axis('off')
        self._save_and_close(fig, output_path, show)