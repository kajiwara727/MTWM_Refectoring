import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from typing import Dict, Any

class VisualizerConfig:
    NODE_SIZE = 3000
    REAGENT_NODE_SIZE = 800
    FONT_SIZE = 9
    STATE_FONT_SIZE = 8
    X_SPACING_TARGET = 6.0
    X_SPACING_NODE = 2.0
    Y_OFFSET_STATE = 0.3      # ノード上部のStateのオフセット
    Y_OFFSET_REAGENT = -0.5    # 試薬ノードの配置オフセット
    # 流量カラーマップの設定
    VOLUME_CMAP = cm.viridis   # 小さい流量（紫）→ 大きい流量（黄色）

class MTWMResultVisualizer:
    """
    MTWMソルバーの出力結果を、流量に応じたエッジカラーで可視化するクラス。
    （エッジ上の数値ラベルを省略し、視認性を向上）
    """
    def __init__(self, solution_data: Dict[str, Any], config: type = VisualizerConfig):
        self.solution = solution_data
        self.config = config
        self.G = nx.DiGraph()
        self.pos = {}
        self._build_graph()

    def _build_graph(self):
        # 1. ミキシングノードの登録
        for node in self.solution.get("nodes", []):
            node_id = node["id"]
            self.G.add_node(node_id, node_type='mixing', **node)
            m, l, k = node_id
            x = m * self.config.X_SPACING_TARGET + k * self.config.X_SPACING_NODE
            y = -l
            self.pos[node_id] = (x, y)

        # 2. 試薬ノードの登録
        for node in self.solution.get("nodes", []):
            mixing_id = node["id"]
            for t_idx, vol in enumerate(node.get('r', [])):
                if vol > 0:
                    reagent_id = (mixing_id, f"reagent_t{t_idx}")
                    self.G.add_node(reagent_id, node_type='reagent', label=f"t{t_idx}", volume=vol)
                    mx, my = self.pos[mixing_id]
                    self.pos[reagent_id] = (mx + (t_idx * 0.4 - 0.2), my + self.config.Y_OFFSET_REAGENT)
                    self.G.add_edge(reagent_id, mixing_id, volume=vol, edge_type='reagent')

        # 3. 木構造エッジの登録
        for edge in self.solution.get("edges", []):
            src, dst, vol = edge["source"], edge["target"], edge["volume"]
            is_intra = (src[0] == dst[0])
            self.G.add_edge(src, dst, volume=vol, edge_type='tree', is_intra=is_intra)

    def draw(self, output_path: str = "output/mtwm_result.png", title: str = "MTWM Optimized Result"):
        fig, ax = plt.subplots(figsize=(18, 12))
        
        mixing_nodes = [n for n, d in self.G.nodes(data=True) if d.get('node_type') == 'mixing']
        reagent_nodes = [n for n, d in self.G.nodes(data=True) if d.get('node_type') == 'reagent']

        # 流量に基づくカラーマッピングの準備
        all_volumes = [d['volume'] for u, v, d in self.G.edges(data=True)]
        if not all_volumes:
            all_volumes = [0]
        min_v, max_v = min(all_volumes), max(all_volumes)
        # 流量が全て同じ場合のエラー回避
        if min_v == max_v:
            min_v, max_v = 0, max_v + 1
            
        norm = mcolors.Normalize(vmin=min_v, vmax=max_v)
        scalar_map = cm.ScalarMappable(norm=norm, cmap=self.config.VOLUME_CMAP)

        # --- 1. ノードとStateラベルの描画 ---
        nx.draw_networkx_nodes(self.G, self.pos, nodelist=mixing_nodes, 
                               node_color="white", node_size=self.config.NODE_SIZE, edgecolors="black", ax=ax)
        mixing_labels = {n: f"ID:({n[0]},{n[1]},{n[2]})\nIn:{self.G.nodes[n]['total_input']}" for n in mixing_nodes}
        nx.draw_networkx_labels(self.G, self.pos, labels=mixing_labels, font_size=self.config.FONT_SIZE, ax=ax)

        for n in mixing_nodes:
            x, y = self.pos[n]
            state_text = f"State: {self.G.nodes[n].get('R', [])}"
            ax.text(x, y + self.config.Y_OFFSET_STATE, state_text, 
                    fontsize=self.config.STATE_FONT_SIZE, ha='center', fontweight='bold', 
                    bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray', boxstyle='round,pad=0.2'))

        # --- 2. 試薬ノードの描画 ---
        nx.draw_networkx_nodes(self.G, self.pos, nodelist=reagent_nodes, 
                               node_shape='s', node_color="orange", node_size=self.config.REAGENT_NODE_SIZE, ax=ax)
        reagent_labels = {n: self.G.nodes[n]['label'] for n in reagent_nodes}
        nx.draw_networkx_labels(self.G, self.pos, labels=reagent_labels, font_size=self.config.FONT_SIZE, ax=ax)

        # --- 3. エッジの描画（流量に応じた色付けのみ。数値ラベルは削除） ---
        for u, v, d in self.G.edges(data=True):
            vol = d['volume']
            edge_color = scalar_map.to_rgba(vol)
            width = 1.5 + (vol * 1.5) # 流量に応じて太さも少し変える
            
            style = 'solid' if d.get('is_intra', True) else 'dashed'
            rad = 0.1 if d['edge_type'] == 'tree' else 0.0
            
            nx.draw_networkx_edges(self.G, self.pos, edgelist=[(u, v)], 
                                   width=width, edge_color=[edge_color], style=style,
                                   arrows=True, arrowsize=20, connectionstyle=f"arc3,rad={rad}", ax=ax)

        # カラーバーの追加（流量の凡例として）
        cbar = fig.colorbar(scalar_map, ax=ax, shrink=0.5, pad=0.05)
        cbar.set_label('Droplet Volume (Flow)', fontsize=10, fontweight='bold')

        self._draw_background_elements(ax)

        plt.title(f"{title}\nTotal waste fluids: {self.solution.get('total_waste_fluids', 0)}", fontsize=16)
        plt.axis('off')
        plt.savefig(output_path, bbox_inches='tight')
        plt.close()

    def _draw_background_elements(self, ax):
        if self.pos:
            x_vals = [x for x, y in self.pos.values() if isinstance(x, (int, float))]
            if not x_vals: return
            x_min, x_max = min(x_vals) - 1, max(x_vals) + 1
            y_levels = sorted(list(set(y for x, y in self.pos.values() if isinstance(y, (int, float)) and y <= 0 and y == int(y))), reverse=True)
            for y_coord in y_levels:
                ax.hlines(y_coord, x_min, x_max, colors="lightgray", linestyles="--", alpha=0.4, zorder=0)
                ax.text(x_max, y_coord, f"Level {int(-y_coord)}", color='gray', fontsize=10, fontweight='bold', va='center')