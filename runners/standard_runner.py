from .base_runner import BaseRunner
from core import apply_auto_factors, build_skeleton_tree, calculate_p_values
from core.solver.problem import MTWMProblem
from visualization import MixingTreeVisualizer 
import os

class StandardRunner(BaseRunner):
    """
    MTWM (Multi-Target Waste Minimization) の標準実行モード。
    ターゲットごとの木構造生成、グラフ拡張、最適化ソルバーの実行を一貫して管理します。
    """

    def run(self):
        print("StandardRunner")
        targets = apply_auto_factors(
            self.config.TARGETS, 
            self.config.MAX_MIXER_SIZE
        )
        
        tree_structures = []

        for target in targets:
            print(f"\n--- ターゲット処理開始: {target.name} ---")

            # ① DFMMアルゴリズム: ボトムアップでの木構造（基本グラフ）の構築
            tree_nodes = build_skeleton_tree(target)
            print(f"  [DFMM] 基本の木構造を生成しました (ノード数: {len(tree_nodes)})")
            # ② P値の計算: 各ノードが担当する液滴の重み（濃度寄与度）を計算
            calculate_p_values(tree_nodes, target.factors)
            print("  [DFMM] 各ノードのP値を計算しました")

            tree_structures.append(tree_nodes)

        problem = MTWMProblem(
            targets=targets,
            tree_structures=tree_structures
        )

        print("[Success] MTWMProblemの定式化が完了しました。")
        
        print("\n[Visualizing] 木構造の画像生成を開始します...")
        mtwm_visualizer = MixingTreeVisualizer(problem)
        
        # outputディレクトリに保存
        os.makedirs("output", exist_ok=True)
        mtwm_visualizer.draw(output_path="output/mtwm_graph.png", title="MTWM Final Problem Structure")