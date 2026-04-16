from .base_runner import BaseRunner
from core import apply_auto_factors, build_skeleton_tree, calculate_p_values
from core.solver.problem import MTWMProblem
from core.solver.solver import MTWMSolver
from visualization.result_visualizer import MTWMResultVisualizer
import os

class StandardRunner(BaseRunner):
    """
    MTWM (Multi-Target Waste Minimization) の標準実行モード。
    定式化、ソルバー実行、最適化結果の可視化を一貫して管理します。
    """

    def run(self):
        print("StandardRunner: 最適化プロセスを開始します。")
        
        # 1. ターゲットの取得と自動因数分解
        targets = apply_auto_factors(
            self.config.TARGETS, 
            self.config.MAX_MIXER_SIZE
        )
        
        tree_structures = []
        for target in targets:
            print(f"  [Build] ターゲットの基本構造を構築中: {target.name}")
            # 木構造の生成とP値（濃度重み）の計算
            tree_nodes = build_skeleton_tree(target)
            calculate_p_values(tree_nodes, target.factors)
            tree_structures.append(tree_nodes)

        # 2. MTWM問題の定式化
        problem = MTWMProblem(
            targets=targets,
            tree_structures=tree_structures
        )
        print("[Success] 問題の定式化が完了しました。")

        # 3. ソルバーの実行
        print("\n--- MTWMソルバー実行 ---")
        # objective_mode は "waste_fluids" を指定
        solver = MTWMSolver(problem, objective_mode="waste_fluids")
        solution = solver.solve()
        
        # 4. 結果の処理と描画
        if solution:
            print(f"\n[Optimization Result]")
            print(f"  Total waste fluids: {solution['total_waste_fluids']}")
            
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "mtwm_optimized_result.png")
            
            print(f"  [Visualizing] 結果を保存中: {output_path}")
            visualizer = MTWMResultVisualizer(solution)
            visualizer.draw(
                output_path=output_path, 
                title="MTWM Optimized Routing & Droplet Flows"
            )
            print("[Finish] すべての工程が正常に完了しました。")
        else:
            print("\n[Error] 実行可能な解が見つかりませんでした。制約条件を確認してください。")