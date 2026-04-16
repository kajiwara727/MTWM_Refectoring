# runners/standard_runner.py
from .base_runner import BaseRunner
from core import apply_auto_factors, build_skeleton_tree, calculate_droplet_weights
from core.solver.problem import MTWMProblem
from core.solver.solver import MTWMSolver

class StandardRunner(BaseRunner):
    """
    MTWM の標準実行モード。
    定式化、ソルバー実行、最適化結果の可視化を一貫して管理します。
    """
    def run(self):
        print("StandardRunner: 最適化プロセスを開始します。")
        
        # 1. ターゲットの取得と構造構築
        targets = apply_auto_factors(self.config.TARGETS, self.config.MAX_MIXER_SIZE)
        tree_structures = []
        for target_id, target in enumerate(targets):
            tree_nodes = build_skeleton_tree(target, target_id=target_id)
            calculate_droplet_weights(tree_nodes, target.factors)
            tree_structures.append(tree_nodes)

        # 2. 問題の定式化
        problem = MTWMProblem(targets=targets, tree_structures=tree_structures)

        self.visualize(mode='problem', data=problem, output_filename="mtwm_problem_structure.png", title="MTWM Problem Structure")

        # 3. ソルバーの実行
        solver = MTWMSolver(problem, objective_mode="waste_fluids")
        solution = solver.solve()
        
        # 4. 結果の可視化
        if solution:
            self.visualize(
                mode='result', 
                data=solution, 
                output_filename="mtwm_optimized_result.png", 
                title="MTWM Optimized Routing & Droplet Flows"
            )
            print("[Finish] すべての工程が正常に完了しました。")
        else:
            print("\n[Error] 解が見つかりませんでした。")