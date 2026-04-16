# runners/standard_runner.py
from .base_runner import BaseRunner
from core import apply_auto_factors, build_complete_skeleton_tree
from core.solver.problem import MTWMProblem
from core.solver.solver import MTWMSolver

class StandardRunner(BaseRunner):
    def run(self):
        # 設定オブジェクトから取得 (DI)
        targets = apply_auto_factors(self.config.targets, self.config.max_mixer_size)
        tree_structures = []
        for target_id, target in enumerate(targets):
            # ファクトリ関数を使用 (副作用の隠蔽)
            tree_nodes = build_complete_skeleton_tree(target, target_id=target_id)
            tree_structures.append(tree_nodes)

        problem = MTWMProblem(targets=targets, tree_structures=tree_structures)
        solver = MTWMSolver(problem, objective_mode="waste_fluids")
        solution = solver.solve()
        
        # 可視化せず、データを返す
        return {"problem": problem, "solution": solution}