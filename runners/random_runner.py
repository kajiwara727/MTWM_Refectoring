# runners/random_runner.py
import random
import math
import os
from functools import reduce
from core.models import Target
from .base_runner import BaseRunner
from core import build_complete_skeleton_tree
from core.solver.problem import MTWMProblem
from core.solver.solver import MTWMSolver
from core.solver.solver_config import SolverConfig
from core.io.targets_io import save_targets
from visualization import export_visualization


class RandomRunner(BaseRunner):
    def run(self) -> dict:
        rc = self.config.random_config
        inputs_log = []
        outputs_log = []

        settings_summary = (
            f"targets{rc.num_targets}_reagents{rc.num_reagents}"
            f"_sum{rc.ratio_sum}_mixer{self.config.max_mixer_size}"
        )
        session_dir = self.create_session_dir(settings_summary)

        for i in range(rc.num_executions):
            exec_id = i + 1
            raw_targets      = self._generate_random_targets(rc.num_targets, rc.num_reagents, rc.ratio_sum)
            processed_targets = self.prepare_targets(raw_targets)

            # ── ターゲットを JSON に保存（後から再利用・比較実験に使える）──
            targets_file = os.path.join(session_dir, f"exec_{exec_id}", "targets.json")
            save_targets(
                raw_targets,
                self.config.max_mixer_size,
                targets_file,
                source="random",
                extra_meta={"execution_id": exec_id},
            )

            # ── ソルバー実行 ───────────────────────────────────────────
            tree_structures = [
                build_complete_skeleton_tree(t, target_id=idx)
                for idx, t in enumerate(processed_targets)
            ]
            problem    = MTWMProblem(targets=processed_targets, tree_structures=tree_structures)
            total_nodes = len(problem.nodes_metadata)
            cfg = SolverConfig.large_mtwm() if total_nodes > 80 else SolverConfig.default_mtwm()
            solver   = MTWMSolver(problem, objective_mode="waste_fluids", solver_config=cfg)
            solution = solver.solve()

            inputs_log.append({
                "execution_id": exec_id,
                "targets":      processed_targets,
                "targets_file": targets_file,   # 保存先パスも記録
            })
            outputs_log.append({
                "execution_id": exec_id,
                "is_success":   solution is not None,
                "solution":     solution,
            })

            print(f"[RandomRunner] exec {exec_id}/{rc.num_executions}  "
                  f"waste={solution.total_waste_fluids if solution else '---'}  "
                  f"-> targets: {targets_file}")

            # ── 可視化 ─────────────────────────────────────────────────
            if rc.visualize and solution:
                img_filename = f"exec_{exec_id}_result.png"
                export_visualization(
                    mode="result",
                    data=solution,
                    filename=img_filename,
                    title=f"Execution {exec_id} Result",
                    output_dir=session_dir,
                )

        self.save_reports(session_dir, {"runs": inputs_log}, {"runs": outputs_log})

        return {
            "session_dir": session_dir,
            "status":      "success",
            "inputs_log":  inputs_log,
        }

    def _generate_random_targets(self, num_targets, num_reagents, ratio_sum):
        targets = []
        for i in range(num_targets):
            while True:
                dividers = sorted(random.sample(range(1, ratio_sum), num_reagents - 1))
                ratios = [a - b for a, b in zip(dividers + [ratio_sum], [0] + dividers)]
                if reduce(math.gcd, ratios) == 1:
                    targets.append(Target(name=f"Exec_Target_{i+1}", ratios=ratios))
                    break
        return targets

    def visualize(self, result_data: dict) -> None:
        # 各ループ内で既に出力済みのため、ここでは何もしない
        pass
