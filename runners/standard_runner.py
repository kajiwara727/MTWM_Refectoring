from .base_runner import BaseRunner
from core import build_complete_skeleton_tree
from core.solver.problem import MTWMProblem
from core.solver.solver import MTWMSolver
from visualization import export_visualization

class StandardRunner(BaseRunner):
    def run(self) -> dict:
        targets = self.prepare_targets(self.config.targets)
        tree_structures = [build_complete_skeleton_tree(t, target_id=idx) for idx, t in enumerate(targets)]

        problem = MTWMProblem(targets=targets, tree_structures=tree_structures)
        solver = MTWMSolver(problem, objective_mode="waste_fluids")
        solution = solver.solve()
        
        settings_summary = f"targets{len(targets)}_mixer{self.config.max_mixer_size}"
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
        
        return {"problem": problem, "solution": solution, "session_dir": session_dir}

    def visualize(self, result_data: dict) -> None:
        session_dir = result_data["session_dir"]
        if result_data.get("solution"):
            export_visualization('problem', result_data["problem"], "mtwm_problem_structure.png", "MTWM Problem Structure", output_dir=session_dir)
            export_visualization('result', result_data["solution"], "mtwm_optimized_result.png", "MTWM Optimized Result", output_dir=session_dir)