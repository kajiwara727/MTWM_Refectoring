# runners/random_runner.py
import random
import math
from functools import reduce
from core.models import Target
from .base_runner import BaseRunner
from core import build_complete_skeleton_tree
from core.solver.problem import MTWMProblem
from core.solver.solver import MTWMSolver
from visualization import export_visualization

class RandomRunner(BaseRunner):
    def run(self) -> dict:
        rc = self.config.random_config
        inputs_log = []
        outputs_log = []

        settings_summary = f"targets{rc.num_targets}_reagents{rc.num_reagents}_sum{rc.ratio_sum}_mixer{self.config.max_mixer_size}"
        session_dir = self.create_session_dir(settings_summary)

        for i in range(rc.num_executions):
            exec_id = i + 1
            raw_targets = self._generate_random_targets(rc.num_targets, rc.num_reagents, rc.ratio_sum)
            processed_targets = self.prepare_targets(raw_targets)
            
            tree_structures = [build_complete_skeleton_tree(t, target_id=idx) for idx, t in enumerate(processed_targets)]

            problem = MTWMProblem(targets=processed_targets, tree_structures=tree_structures)
            solver = MTWMSolver(problem)
            solution = solver.solve()

            inputs_log.append({"execution_id": exec_id, "targets": processed_targets})
            outputs_log.append({"execution_id": exec_id, "is_success": solution is not None, "solution": solution})

            # ランダムモード特有の各ループ内での描画処理
            if rc.visualize and solution:
                img_filename = f"exec_{exec_id}_result.png"
                export_visualization(
                    mode='result', 
                    data=solution, 
                    filename=img_filename, 
                    title=f"Execution {exec_id} Result",
                    output_dir=session_dir
                )

        self.save_reports(session_dir, {"runs": inputs_log}, {"runs": outputs_log})
        
        return {"session_dir": session_dir, "status": "success"}

    def _generate_random_targets(self, num_targets, num_reagents, ratio_sum):
        targets = []
        for i in range(num_targets):
            while True:
                dividers = sorted(random.sample(range(1, ratio_sum), num_reagents - 1))
                ratios = [a - b for a, b in zip(dividers + [ratio_sum], [0] + dividers)]
                if reduce(math.gcd, ratios) == 1:
                    targets.append(Target(name=f'Exec_Target_{i+1}', ratios=ratios))
                    break
        return targets

    def visualize(self, result_data: dict) -> None:
        # ランダムモードの画像はループ処理(run内部)で既に出力済みのため、ここでは何もしない
        pass