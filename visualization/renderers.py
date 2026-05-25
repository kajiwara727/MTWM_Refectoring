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

class ExtensionProblemRenderer(BaseRenderer):
    """拡張ノード候補を含む問題グラフのレンダラー"""

    def render(self, output_path: str, title: str, show: bool = False) -> None:
        import matplotlib.patches as mpatches
        fig, ax = plt.subplots(figsize=(16, 10))

        regular_nodes = [n for n, d in self.G.nodes(data=True) if d.get("node_kind") == "regular"]
        ext_nodes     = [n for n, d in self.G.nodes(data=True) if d.get("node_kind") == "extension"]

        reg_colors = ["lightgreen" if d.get("is_leaf") else "skyblue"
                      for n, d in self.G.nodes(data=True) if d.get("node_kind") == "regular"]
        reg_labels = {
            n: f"({n.target_id},{n.level},{n.index})\nP:{d.get('droplet_weight','-')}"
            for n, d in self.G.nodes(data=True) if d.get("node_kind") == "regular"
        }
        ext_labels = {
            n: d.get("label", str(n))
            for n, d in self.G.nodes(data=True) if d.get("node_kind") == "extension"
        }

        nx.draw_networkx_nodes(self.G, self.pos, nodelist=regular_nodes,
                               node_color=reg_colors, node_size=self.config.NODE_SIZE,
                               edgecolors="black", ax=ax)
        nx.draw_networkx_nodes(self.G, self.pos, nodelist=ext_nodes,
                               node_color="plum", node_size=self.config.NODE_SIZE * 1.2,
                               node_shape="D", edgecolors="purple", ax=ax)
        nx.draw_networkx_labels(self.G, self.pos, labels={**reg_labels, **ext_labels},
                                font_size=self.config.FONT_SIZE, ax=ax)

        for etype, color, rad in [
            ("default",       "black",  0.0),
            ("potential",     "red",    0.2),
            ("ext_input",     "purple", 0.15),
            ("ext_potential", "orange", 0.25),
        ]:
            edges = [(u, v) for u, v, d in self.G.edges(data=True) if d.get("edge_type") == etype]
            if edges:
                nx.draw_networkx_edges(self.G, self.pos, edgelist=edges,
                                       edge_color=color, width=1.2, arrows=True,
                                       arrowsize=self.config.ARROW_SIZE,
                                       connectionstyle=f"arc3,rad={rad}", ax=ax)

        self._draw_background_levels(ax)
        handles = [
            mpatches.Patch(color="black",  label="Default"),
            mpatches.Patch(color="red",    label="Potential (MTWM)"),
            mpatches.Patch(color="purple", label="Ext. Node Input"),
            mpatches.Patch(color="orange", label="Ext. Node Output Candidate"),
            mpatches.Patch(color="plum",   label="Extension Node"),
        ]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0.)
        plt.tight_layout()
        plt.title(title, fontsize=13)
        self._save_and_close(fig, output_path, show)


class ExtensionResultRenderer(BaseRenderer):
    """拡張ノードを含む最適化結果グラフのレンダラー"""

    def render(self, output_path: str, title: str, total_waste: int = 0, show: bool = False) -> None:
        import matplotlib.patches as mpatches
        import matplotlib.colors as mcolors
        import matplotlib.cm as cm

        fig, ax = plt.subplots(figsize=(20, 13))

        regular_nodes = [n for n, d in self.G.nodes(data=True) if d.get("node_kind") == "regular"]
        ext_nodes     = [n for n, d in self.G.nodes(data=True) if d.get("node_kind") == "extension"]
        reagent_nodes = [n for n, d in self.G.nodes(data=True) if d.get("node_kind") == "reagent"]

        all_volumes = [d["volume"] for _, _, d in self.G.edges(data=True) if "volume" in d] or [0]
        norm = mcolors.Normalize(vmin=min(all_volumes), vmax=max(all_volumes) + 1)
        scalar_map = cm.ScalarMappable(norm=norm, cmap=self.config.VOLUME_CMAP)

        # 通常ノード
        nx.draw_networkx_nodes(self.G, self.pos, nodelist=regular_nodes,
                               node_color="white", node_size=self.config.RESULT_NODE_SIZE,
                               edgecolors="black", ax=ax)
        reg_labels = {
            n: f"({n.target_id},{n.level},{n.index})\nIn:{d['node_res'].total_input}"
            for n, d in self.G.nodes(data=True) if d.get("node_kind") == "regular"
        }
        nx.draw_networkx_labels(self.G, self.pos, labels=reg_labels,
                                font_size=self.config.FONT_SIZE, ax=ax)

        for n, d in self.G.nodes(data=True):
            if d.get("node_kind") == "regular":
                x, y = self.pos[n]
                state = d["node_res"].concentration_state
                ax.text(x, y + self.config.Y_OFFSET_STATE, f"{state}",
                        fontsize=self.config.STATE_FONT_SIZE, ha="center",
                        fontweight="bold",
                        bbox=dict(facecolor="white", alpha=0.9, edgecolor="gray", boxstyle="round,pad=0.2"))

        # 拡張ノード
        nx.draw_networkx_nodes(self.G, self.pos, nodelist=ext_nodes,
                               node_color="plum", node_size=self.config.RESULT_NODE_SIZE * 1.1,
                               node_shape="D", edgecolors="purple", ax=ax)
        ext_labels = {
            n: d.get("label", "") for n, d in self.G.nodes(data=True) if d.get("node_kind") == "extension"
        }
        nx.draw_networkx_labels(self.G, self.pos, labels=ext_labels,
                                font_size=self.config.FONT_SIZE, ax=ax)

        # 試薬ノード
        nx.draw_networkx_nodes(self.G, self.pos, nodelist=reagent_nodes,
                               node_shape="s", node_color="orange",
                               node_size=self.config.REAGENT_NODE_SIZE, ax=ax)
        nx.draw_networkx_labels(self.G, self.pos,
                                labels={n: d["label"] for n, d in self.G.nodes(data=True) if d.get("node_kind") == "reagent"},
                                font_size=self.config.FONT_SIZE, ax=ax)

        # エッジ描画
        for u, v, d in self.G.edges(data=True):
            vol = d.get("volume", 0)
            edge_color = scalar_map.to_rgba(vol)
            width = 1.5 + vol * 1.5
            etype = d.get("edge_type", "tree")
            style = "dashed" if etype == "extension" else "solid"
            rad   = 0.15 if etype == "extension" else (0.1 if not d.get("is_intra", True) else 0.0)
            nx.draw_networkx_edges(self.G, self.pos, edgelist=[(u, v)],
                                   width=width, edge_color=[edge_color], style=style,
                                   arrows=True, arrowsize=20,
                                   connectionstyle=f"arc3,rad={rad}", ax=ax)

        cbar = fig.colorbar(scalar_map, ax=ax, shrink=0.5, pad=0.05)
        cbar.set_label("Droplet Volume", fontsize=10, fontweight="bold")

        handles = [
            mpatches.Patch(color="white", label="Regular Mixing Node"),
            mpatches.Patch(color="plum",  label="Extension Node (proposed)"),
            mpatches.Patch(color="orange",label="Reagent"),
        ]
        ax.legend(handles=handles, loc="upper left")

        self._draw_background_levels(ax)
        plt.title(f"{title}   [Total waste: {total_waste}]", fontsize=14)
        plt.axis("off")
        self._save_and_close(fig, output_path, show)


class ProposedHeuristicRenderer(BaseRenderer):
    def render(self, output_path: str, title: str, show: bool = False) -> None:
        fig, ax = plt.subplots(figsize=(14, 9))
        
        # 試薬ごとのカラーパレット (T0:赤系, T1:青系, T2:緑系, T3:オレンジ系...)
        palette = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0']
        node_colors = []
        labels = {}
        
        # 追加: 実際にグラフ内で単独最多となった試薬のインデックスを記録するセット
        used_reagents = set()
        
        for n, d in self.G.nodes(data=True):
            dom = d.get('dominant_reagents', set())
            
            if not dom:
                color = 'lightgray'
                dom_str = "None"
            elif len(dom) == 1:
                r_idx = list(dom)[0]
                color = palette[r_idx % len(palette)]
                dom_str = f"T{r_idx}"
                used_reagents.add(r_idx)  # 使用された試薬を記録
            else:
                color = '#ffb3e6'
                dom_str = ",".join([f"T{r}" for r in sorted(dom)])
                
            node_colors.append(color)
            labels[n] = f"ID:({n.target_id},{n.level},{n.index})\nDom:[{dom_str}]"
            
        nx.draw_networkx_nodes(self.G, self.pos, ax=ax, node_color=node_colors, node_size=self.config.NODE_SIZE, edgecolors="black")
        nx.draw_networkx_labels(self.G, self.pos, ax=ax, labels=labels, font_size=self.config.FONT_SIZE)

        default_edges = [(u, v) for u, v, d in self.G.edges(data=True) if d['edge_type'] == 'default']
        potential_edges = [(u, v) for u, v, d in self.G.edges(data=True) if d['edge_type'] == 'heuristic_potential']

        if default_edges:
            nx.draw_networkx_edges(self.G, self.pos, ax=ax, edgelist=default_edges, edge_color='black', width=1.5, arrows=True, arrowsize=self.config.ARROW_SIZE)
        if potential_edges:
            nx.draw_networkx_edges(self.G, self.pos, ax=ax, edgelist=potential_edges, edge_color='blue', width=1.0, arrows=True, arrowsize=self.config.ARROW_SIZE, connectionstyle="arc3,rad=0.2")

        self._draw_background_levels(ax)
        
        # ▼ 修正: 凡例を動的に構築する
        handles = []
        
        # 1. 動的に取得した試薬の色を凡例に追加
        for r_idx in sorted(used_reagents):
            color = palette[r_idx % len(palette)]
            handles.append(mpatches.Patch(color=color, label=f'Dominant: Reagent T{r_idx}'))
            
        # 2. その他の状態（複数同数、割り当てなし）とエッジの凡例を追加
        handles.extend([
            mpatches.Patch(color='#ffb3e6', label='Multiple Dominant'),
            mpatches.Patch(color='lightgray', label='No Dominant'),
            mpatches.Patch(color='black', label='Default Connection'),
            mpatches.Patch(color='blue', label='Allowed Connection (Heuristic)')
        ])
        
        # bbox_to_anchor を使ってグラフの枠外（右側）に凡例を配置
        ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0.)
        
        # グラフのレイアウトを調整（枠外の凡例が見切れないようにする）
        plt.tight_layout()
        
        plt.title(title, fontsize=14)
        self._save_and_close(fig, output_path, show)