from .base_runner import BaseRunner
from core import build_complete_dfmm_tree
from core.solver.proposed_problem import ProposedMTWMProblem
from core.solver.solver import MTWMSolver
from visualization import export_visualization

class ProposedRunner(BaseRunner):
    """提案手法（ヒューリスティックによる経路削減）を実行するランナー"""
    
    def run(self) -> dict:
        targets = self.prepare_targets(self.config.targets)
        
        # 1. DFMMツリーを構築（ここで仮の試薬割り当て r が決まる）
        tree_structures = [build_complete_dfmm_tree(t, target_id=idx) for idx, t in enumerate(targets)]

        # 2. 提案手法用のProblemクラスを使用（最多試薬が一致しないエッジを削減）
        problem = ProposedMTWMProblem(targets=targets, tree_structures=tree_structures)
        solver = MTWMSolver(problem, objective_mode="waste_fluids")
        solution = solver.solve()
        
        settings_summary = f"proposed_targets{len(targets)}_mixer{self.config.max_mixer_size}"
        session_dir = self.create_session_dir(settings_summary)
        
        input_data = {"max_mixer_size": self.config.max_mixer_size, "targets": targets}
        output_data = {
            "is_success": solution is not None,
            "solution": solution,
            "summary": {
                "objective_value": solution.objective_value if solution else None,
                "total_waste_fluids": solution.total_waste_fluids if solution else None
            }
        }
        self.save_reports(session_dir, input_data, output_data)
        
        # visualizeメソッドで使えるように、tree_structuresも辞書に含めて返す
        return {
            "problem": problem, 
            "solution": solution, 
            "session_dir": session_dir,
            "tree_structures": tree_structures
        }

    def visualize(self, result_data: dict) -> None:
        session_dir = result_data["session_dir"]
        
        if result_data.get("solution"):
            export_visualization('problem', result_data["problem"], "proposed_problem_structure.png", "Proposed Problem Structure", output_dir=session_dir)
            export_visualization('result', result_data["solution"], "proposed_optimized_result.png", "Proposed Optimized Result", output_dir=session_dir)
        
        # ▼ 変更: 各ノードがどの試薬で分類されたかを色分けしたグラフを出力
        if result_data.get("problem"):
            export_visualization(
                'heuristic', 
                result_data["problem"], 
                "proposed_heuristic_classification.png", 
                "Node Classification by Dominant Reagent", 
                output_dir=session_dir
            )