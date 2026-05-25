# runners/compare_runner.py
"""
【比較実験】同一ターゲットで MTWM と提案手法（拡張ノード）を順番に実行して比較するランナー。

使い方:
    # ランダムターゲットで比較
    python main.py --mode compare

    # 保存済みターゲットを使って比較
    python main.py --mode compare --from-file output/random/.../exec_1/targets.json

    # config.py の targets を直接使って比較
    python main.py --mode compare   # config.py の targets が設定されていれば使用

比較レポートの出力:
    {session_dir}/compare_report.txt   ← 並列比較サマリ
    {session_dir}/targets.json         ← 後から再利用可能なターゲット設定
    {session_dir}/input.json           ← 標準入力レポート
    {session_dir}/output.json          ← 標準出力レポート
"""

import math
import random
from functools import reduce
from typing import List, Optional

from .base_runner import BaseRunner
from core.models import Target
from core import build_complete_skeleton_tree, build_complete_dfmm_tree
from core.solver.problem import MTWMProblem
from core.solver.extension_problem import ExtensionMTWMProblem
from core.solver.solver import MTWMSolver
from core.solver.extension_solver import ExtensionMTWMSolver
from core.solver.solver_config import SolverConfig
from core.solver.dto import OptimizationResult
from core.io.targets_io import save_targets
from core.algorithm.extension import describe_extension_nodes
from utils.exporters import CompareTextExporter
from visualization import export_visualization


class CompareRunner(BaseRunner):
    """
    同一ターゲットで MTWM と提案手法（Extension）を順番に実行し結果を比較する。

    ターゲット取得の優先順位:
      1. config.targets が空でない → そのターゲットを使用
      2. config.random_config が設定されている → ランダム生成して使用
    """

    def __init__(self, config):
        super().__init__(config)
        # 比較専用レポーターを追加
        self.exporters.append(CompareTextExporter())

    # ------------------------------------------------------------------
    # メイン実行
    # ------------------------------------------------------------------

    def run(self) -> dict:
        # ── ターゲットの取得 ──────────────────────────────────────
        if self.config.targets:
            raw_targets = list(self.config.targets)
            print(f"[CompareRunner] 設定済みターゲット {len(raw_targets)} 件を使用")
        else:
            rc = self.config.random_config
            if rc is None:
                raise ValueError(
                    "compare モードでは config.targets または random_config が必要です。"
                )
            raw_targets = self._generate_random_targets(
                rc.num_targets, rc.num_reagents, rc.ratio_sum
            )
            print(f"[CompareRunner] ランダムターゲット {len(raw_targets)} 件を生成")

        targets = self.prepare_targets(raw_targets)

        # ── セッションディレクトリ ─────────────────────────────────
        settings_summary = (
            f"compare_targets{len(targets)}_mixer{self.config.max_mixer_size}"
        )
        session_dir = self.create_session_dir(settings_summary)

        # ── ターゲット保存（後から再利用可能）──────────────────────
        targets_file = f"{session_dir}/targets.json"
        save_targets(
            raw_targets, self.config.max_mixer_size, targets_file, source="compare"
        )
        print(f"[CompareRunner] ターゲット保存: {targets_file}")

        # ── 1. MTWM (ベースライン) 実行 ───────────────────────────
        print(f"\n{'='*56}")
        print("  [1/2] MTWM (ベースライン) を実行中...")
        print(f"{'='*56}")
        mtwm_solution = self._run_mtwm(targets)

        # ── 2. Extension (提案手法) 実行 ───────────────────────────
        print(f"\n{'='*56}")
        print("  [2/2] Extension (提案手法) を実行中...")
        print(f"{'='*56}")
        ext_solution, ext_problem = self._run_extension(targets)

        # ── 比較サマリを標準出力に表示 ────────────────────────────
        self._print_comparison(targets, mtwm_solution, ext_solution)

        # ── レポート保存 ──────────────────────────────────────────
        input_data = {
            "max_mixer_size": self.config.max_mixer_size,
            "targets": targets,
            "targets_file": targets_file,
        }
        output_data = {
            "mtwm": {
                "is_success": mtwm_solution is not None,
                "solution": mtwm_solution,
            },
            "extension": {
                "is_success": ext_solution is not None,
                "solution": ext_solution,
            },
        }
        self.save_reports(session_dir, input_data, output_data)

        return {
            "session_dir":        session_dir,
            "targets":            targets,
            "targets_file":       targets_file,
            "mtwm_solution":      mtwm_solution,
            "extension_solution": ext_solution,
            "extension_problem":  ext_problem,
        }

    # ------------------------------------------------------------------
    # MTWM 実行
    # ------------------------------------------------------------------

    def _run_mtwm(self, targets: List[Target]) -> Optional[OptimizationResult]:
        tree_structures = [
            build_complete_skeleton_tree(t, target_id=idx)
            for idx, t in enumerate(targets)
        ]
        problem    = MTWMProblem(targets=targets, tree_structures=tree_structures)
        total_nodes = len(problem.nodes_metadata)
        cfg = SolverConfig.large_mtwm() if total_nodes > 80 else SolverConfig.default_mtwm()
        solver = MTWMSolver(problem, objective_mode="waste_fluids", solver_config=cfg)
        return solver.solve()

    # ------------------------------------------------------------------
    # Extension 実行
    # ------------------------------------------------------------------

    def _run_extension(
        self, targets: List[Target]
    ) -> tuple[Optional[OptimizationResult], Optional[ExtensionMTWMProblem]]:
        tree_structures = [
            build_complete_dfmm_tree(t, target_id=idx)
            for idx, t in enumerate(targets)
        ]
        problem = ExtensionMTWMProblem(
            targets=targets,
            tree_structures=tree_structures,
            max_mixer_size=self.config.max_mixer_size,
        )
        print(f"    拡張ノード: {len(problem.extension_nodes)} 件")
        if problem.extension_nodes:
            print(describe_extension_nodes(problem.extension_nodes))

        total_nodes = len(problem.nodes_metadata)
        ext_nodes   = len(problem.extension_nodes)
        cfg = (
            SolverConfig.large_extension()
            if total_nodes > 80 or ext_nodes > 20
            else SolverConfig.default_extension()
        )
        solver   = ExtensionMTWMSolver(problem, objective_mode="waste_fluids", solver_config=cfg)
        solution = solver.solve()
        return solution, problem

    # ------------------------------------------------------------------
    # ランダムターゲット生成
    # ------------------------------------------------------------------

    def _generate_random_targets(
        self, num_targets: int, num_reagents: int, ratio_sum: int
    ) -> List[Target]:
        targets = []
        for i in range(num_targets):
            while True:
                dividers = sorted(random.sample(range(1, ratio_sum), num_reagents - 1))
                ratios   = [a - b for a, b in zip(dividers + [ratio_sum], [0] + dividers)]
                if reduce(math.gcd, ratios) == 1:
                    targets.append(Target(name=f"Target_{i+1}", ratios=ratios))
                    break
        return targets

    # ------------------------------------------------------------------
    # 比較サマリ（標準出力）
    # ------------------------------------------------------------------

    def _print_comparison(self, targets, mtwm_sol, ext_sol) -> None:
        print(f"\n{'='*64}")
        print("  比較結果サマリ".center(64))
        print(f"{'='*64}")
        print("  [Targets]")
        for t in targets:
            print(f"    - {t.name}: {t.ratios}  (sum={sum(t.ratios)})")
        print()

        header = f"  {'手法':<22} {'廃棄液量':>8}  {'実行時間':>12}  状態"
        print(header)
        print(f"  {'-'*56}")

        def row(label, sol):
            if sol is None:
                return f"  {label:<22} {'---':>8}  {'---':>12}  NO SOLUTION"
            w = sol.total_waste_fluids
            t = sol.execution_time
            return f"  {label:<22} {w:>8}  {t:>10.2f}s  OK"

        print(row("MTWM (baseline)", mtwm_sol))
        print(row("Extension (提案手法)", ext_sol))
        print()

        if mtwm_sol and ext_sol:
            diff = mtwm_sol.total_waste_fluids - ext_sol.total_waste_fluids
            pct  = (diff / mtwm_sol.total_waste_fluids * 100
                    if mtwm_sol.total_waste_fluids > 0 else 0.0)
            print(f"  廃棄液削減量: {diff:+d}  ({pct:+.1f}%)")
            if diff > 0:
                print("  -> 提案手法が優れています [WIN]")
            elif diff == 0:
                print("  -> 同等の結果です [DRAW]")
            else:
                print("  -> MTWM の方が少ない廃棄液でした [MTWM WIN]")

        print(f"{'='*64}\n")

    # ------------------------------------------------------------------
    # 可視化
    # ------------------------------------------------------------------

    def visualize(self, result_data: dict) -> None:
        session_dir = result_data["session_dir"]
        mtwm_sol    = result_data.get("mtwm_solution")
        ext_sol     = result_data.get("extension_solution")
        ext_problem = result_data.get("extension_problem")

        if mtwm_sol:
            export_visualization(
                "result",
                mtwm_sol,
                "compare_mtwm_result.png",
                f"MTWM Result  (waste={mtwm_sol.total_waste_fluids})",
                output_dir=session_dir,
            )
        if ext_sol and ext_problem:
            export_visualization(
                "extension_result",
                {"solution": ext_sol, "problem": ext_problem},
                "compare_extension_result.png",
                f"Extension Result  (waste={ext_sol.total_waste_fluids})",
                output_dir=session_dir,
            )
