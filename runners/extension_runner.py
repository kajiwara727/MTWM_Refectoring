# runners/extension_runner.py
"""
【提案手法】拡張ノードを使用するランナー。

処理フロー:
  1. DFMMツリーを構築（骨格ツリー + 試薬仮割り当て）
  2. ExtensionMTWMProblem: 拡張ノードを生成し問題を構築
  3. ExtensionMTWMSolver: CP-SAT で最適化
  4. 結果の保存・可視化
"""

from .base_runner import BaseRunner
from core import build_complete_dfmm_tree
from core.solver.extension_problem import ExtensionMTWMProblem
from core.solver.extension_solver import ExtensionMTWMSolver
from core.solver.solver_config import SolverConfig
from core.algorithm.extension import describe_extension_nodes
from visualization import export_visualization


class ExtensionRunner(BaseRunner):
    """拡張ノード提案手法を実行するランナー"""

    def run(self) -> dict:
        targets = self.prepare_targets(self.config.targets)

        # 1. DFMMツリーを構築（仮の試薬割り当て r が決まる）
        tree_structures = [
            build_complete_dfmm_tree(t, target_id=idx)
            for idx, t in enumerate(targets)
        ]

        # 2. 拡張ノード入り問題クラスを構築
        problem = ExtensionMTWMProblem(
            targets=targets,
            tree_structures=tree_structures,
            max_mixer_size=self.config.max_mixer_size,
        )

        print(f"[ExtensionRunner] 拡張ノード:")
        print(describe_extension_nodes(problem.extension_nodes))

        # 3. 問題規模に応じてプリセットを自動選択
        total_nodes = len(problem.nodes_metadata)
        ext_nodes   = len(problem.extension_nodes)
        if total_nodes > 80 or ext_nodes > 20:
            cfg = SolverConfig.large_extension()
        else:
            cfg = SolverConfig.default_extension()

        # 4. ソルバーで最適化
        solver = ExtensionMTWMSolver(
            problem, objective_mode="waste_fluids", solver_config=cfg
        )
        solution = solver.solve()

        # 4. セッションディレクトリの作成
        settings_summary = (
            f"ext_targets{len(targets)}_mixer{self.config.max_mixer_size}"
        )
        session_dir = self.create_session_dir(settings_summary)

        # 5. レポート保存
        input_data = {
            "max_mixer_size": self.config.max_mixer_size,
            "targets": targets,
            "num_extension_nodes": len(problem.extension_nodes),
        }
        output_data = {
            "is_success": solution is not None,
            "solution": solution,
            "summary": {
                "objective_value": solution.objective_value if solution else None,
                "total_waste_fluids": solution.total_waste_fluids if solution else None,
                "active_extension_nodes": (
                    len(solution.extension_nodes) if solution else 0
                ),
            },
        }
        self.save_reports(session_dir, input_data, output_data)

        return {
            "problem": problem,
            "solution": solution,
            "session_dir": session_dir,
            "tree_structures": tree_structures,
        }

    def visualize(self, result_data: dict) -> None:
        session_dir = result_data["session_dir"]
        solution = result_data.get("solution")
        problem = result_data.get("problem")

        if solution:
            # 最適化結果グラフ（拡張ノードを含む）
            export_visualization(
                "extension_result",
                {"solution": solution, "problem": problem},
                "extension_optimized_result.png",
                f"Extension-MTWM Optimized Result  "
                f"(waste={solution.total_waste_fluids})",
                output_dir=session_dir,
            )

        if problem:
            # 問題グラフ（拡張ノードの接続候補を含む）
            export_visualization(
                "extension_problem",
                problem,
                "extension_problem_structure.png",
                "Extension-MTWM Problem Structure",
                output_dir=session_dir,
            )
