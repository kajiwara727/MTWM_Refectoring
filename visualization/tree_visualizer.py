import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, Any, Callable, Optional

# クラス変数としてレイアウトの定数を抽出し、外部から変更可能にする
class VisualizerConfig:
    NODE_SIZE = 1500
    FONT_SIZE = 8
    ARROW_SIZE = 15
    X_SPACING_MTWM_TARGET = 4.0
    X_SPACING_NODE = 1.2

class MixingTreeVisualizer:
    def __init__(self, data: Any, config: type = VisualizerConfig):
        self.config = config
        self.G = nx.DiGraph()
        self.pos = {}
        
        self.node_color_func: Callable[[Dict[str, Any]], str] = self._default_node_color
        self.node_label_func: Callable[[Dict[str, Any]], str] = self._default_node_label
        
        self._build_graph(data)

    def _build_graph(self, data: Any):
        # 厳密なクラス名判定、またはアダプターを介した判定に変更
        class_name = data.__class__.__name__
        if class_name == "MTWMProblem":
            self._build_mtwm_graph(data)
        elif isinstance(data, dict):
            self._build_dfmm_graph(data)
        else:
            raise TypeError(f"Unsupported data type: {type(data)}")

    def _build_mtwm_graph(self, problem):
        nodes_metadata = problem.nodes_metadata
        for idx, data in nodes_metadata.items():
            m, l, k = idx
            self.G.add_node(idx, **data)
            
            x = m * 4.0 + k * 1.2
            self.pos[idx] = (x, -l)

        for dst_idx, sources in problem.potential_sources_map.items():
            for src_idx in sources:
                dst_node_obj = nodes_metadata[dst_idx]['obj']
                m_dst, m_src = dst_idx[0], src_idx[0]
                
                # 🌟 修正: ターゲットID (m) が一致しているかどうかの判定を追加
                is_default_edge = (m_src == m_dst) and any(child.id == (src_idx[1], src_idx[2]) for child in dst_node_obj.children)
                
                color, edge_type = ('black', 'default') if is_default_edge else ('red', 'potential')
                self.G.add_edge(src_idx, dst_idx, edge_type=edge_type, color=color, weight=1.5 if is_default_edge else 1.0)

    def _build_dfmm_graph(self, tree_nodes: dict):
        for idx, node_obj in tree_nodes.items():
            l, k = idx
            self.G.add_node(idx, obj=node_obj, is_leaf=(l == 0), p_value=node_obj.p_value)
            # マジックナンバーを排除
            self.pos[idx] = (k * self.config.X_SPACING_NODE, -l)
            for child in node_obj.children:
                self.G.add_edge(child.id, idx, edge_type='default', color='black', weight=1.5)

    def _default_node_color(self, data: Dict[str, Any]) -> str:
        return "lightgreen" if data.get('is_leaf') else "skyblue"

    def _default_node_label(self, data: Dict[str, Any]) -> str:
        # モデルへの過度な依存を減らすため、安全に取得
        node_obj = data.get('obj')
        if not node_obj: return "Unknown"
        
        label_parts = [f"ID:{node_obj.id}", f"P:{data.get('p_value', '-')}"]
        
        # hasattrによる暗黙の依存は残るが、取得失敗時にクラッシュしないよう保護
        dispense = getattr(node_obj, 'dispense_inputs', None)
        if dispense:
            label_parts.append(f"Reagents:\n{dispense}")
            
        return "\n".join(label_parts)

    def draw(self, output_path: str = "mtwm_graph.png", show: bool = False, title: str = "Mixing Tree Structure"):
        fig, ax = plt.subplots(figsize=(12, 8))
        
        try:
            node_colors = [self.node_color_func(self.G.nodes[n]) for n in self.G.nodes]
            labels = {n: self.node_label_func(self.G.nodes[n]) for n in self.G.nodes}

            # 🌟 修正: ノードとラベルを先に描画
            nx.draw_networkx_nodes(self.G, self.pos, ax=ax, node_color=node_colors, node_size=1500, edgecolors="black")
            nx.draw_networkx_labels(self.G, self.pos, ax=ax, labels=labels, font_size=8)

            # エッジを属性で分類
            default_edges = [(u, v) for u, v, d in self.G.edges(data=True) if d['edge_type'] == 'default']
            potential_edges = [(u, v) for u, v, d in self.G.edges(data=True) if d['edge_type'] == 'potential']

            # 🌟 修正: デフォルトエッジは直線で太く
            if default_edges:
                nx.draw_networkx_edges(
                    self.G, self.pos, ax=ax, edgelist=default_edges,
                    edge_color='black', width=1.5, arrows=True, arrowsize=15
                )

            # 🌟 修正: 潜在エッジ(赤)は弧(arc3)を描かせて直線との重なりを回避
            if potential_edges:
                nx.draw_networkx_edges(
                    self.G, self.pos, ax=ax, edgelist=potential_edges,
                    edge_color='red', width=1.0, arrows=True, arrowsize=15,
                    connectionstyle="arc3,rad=0.2"  # ここで曲がり具合を調整
                )

            # 背景の破線など
            x_vals = [x for x, y in self.pos.values()]
            if x_vals:
                x_min, x_max = min(x_vals) - 1, max(x_vals) + 2
                y_levels = set(y for x, y in self.pos.values())
                for y_coord in y_levels:
                    ax.hlines(y_coord, x_min, x_max, colors="gray", linestyles="dashed", zorder=0)
                    ax.text(x_max, y_coord, f"Level {int(-y_coord)}", va='center', ha='left', color='coral', fontsize=12, fontweight='bold')

            handles = [mpatches.Patch(color='black', label='Default Connection')]
            if potential_edges:
                handles.append(mpatches.Patch(color='red', label='Potential Connection (Sharing)'))
            ax.legend(handles=handles, loc='upper left')

            plt.title(title, fontsize=14)
            plt.savefig(output_path, bbox_inches='tight')
            
            if show:
                plt.show()
                
        finally:
            plt.close(fig)