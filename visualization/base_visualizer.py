from abc import ABC, abstractmethod
import networkx as nx
import matplotlib.pyplot as plt
from typing import Any
from .config import VisualizerConfig

class BaseVisualizer(ABC):
    """すべての可視化クラスの基底クラス"""
    def __init__(self, config: type = VisualizerConfig):
        self.config = config
        self.G = nx.DiGraph()
        self.pos = {}

    @abstractmethod
    def _build_graph(self, data: Any) -> None:
        """データからNetworkXのグラフと座標(pos)を構築する。サブクラスで実装"""
        pass

    @abstractmethod
    def draw(self, output_path: str, title: str, show: bool = False) -> None:
        """グラフの描画ロジック。サブクラスで実装"""
        pass

    def _draw_background_levels(self, ax: plt.Axes) -> None:
        """Y座標に基づいたレベルの破線とテキストを共通描画"""
        if not self.pos:
            return
            
        x_vals = [x for x, y in self.pos.values() if isinstance(x, (int, float))]
        if not x_vals:
            return
            
        x_min, x_max = min(x_vals) - 1, max(x_vals) + 2
        y_levels = sorted(list(set(y for x, y in self.pos.values() if isinstance(y, (int, float)) and y <= 0 and y == int(y))), reverse=True)
        
        for y_coord in y_levels:
            ax.hlines(y_coord, x_min, x_max, colors="gray", linestyles="dashed", alpha=0.5, zorder=0)
            level_num = int(-y_coord)
            ax.text(x_max, y_coord, f"Level {level_num}", color='coral', fontsize=12, fontweight='bold', va='center')

    def _save_and_close(self, fig: plt.Figure, output_path: str, show: bool) -> None:
        """画像の保存とクリーンアップ"""
        plt.savefig(output_path, bbox_inches='tight')
        if show:
            plt.show()
        plt.close(fig)