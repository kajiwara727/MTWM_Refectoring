import json
import os
from abc import ABC, abstractmethod
from utils.io_manager import MTWMEncoder
from typing import Optional

class ReportExporter(ABC):
    """出力ロジックの抽象インターフェース"""
    @abstractmethod
    def export(self, directory: str, input_data: dict, output_data: dict) -> None:
        pass

class JsonExporter(ReportExporter):
    """JSON形式での出力を担当"""
    def export(self, directory: str, input_data: dict, output_data: dict) -> None:
        with open(os.path.join(directory, "input.json"), 'w', encoding='utf-8') as f:
            json.dump(input_data, f, cls=MTWMEncoder, ensure_ascii=False, indent=2)
            
        with open(os.path.join(directory, "output.json"), 'w', encoding='utf-8') as f:
            json.dump(output_data, f, cls=MTWMEncoder, ensure_ascii=False, indent=2)

class TextExporter(ReportExporter):
    """テキスト形式でのサマリ出力を担当"""
    def export(self, directory: str, input_data: dict, output_data: dict) -> None:
        lines = []
        lines.append("="*60)
        lines.append(" MTWM Optimization Comprehensive Report ".center(60))
        lines.append("="*60)
        lines.append("")

        # どんなRunnerでも "runs" というキーをリストとして扱う（ない場合は単発としてリスト化）
        inputs_list = input_data.get("runs", [input_data])
        outputs_list = output_data.get("runs", [output_data])

        num_execs = len(outputs_list)
        if num_execs > 1:
            lines.append(f"Mode: Batch Execution (Total: {num_execs} runs)")
        else:
            lines.append(f"Mode: Single Execution")
        lines.append("")

        total_waste = 0
        total_time = 0.0
        success_count = 0

        # 全ての実行を統一的に処理
        for idx, (inp, out) in enumerate(zip(inputs_list, outputs_list)):
            run_id = out.get("execution_id", idx + 1)
            solution = out.get("solution")
            targets = inp.get("targets", [])
            
            self._build_single_report(lines, targets, solution, f"Run #{run_id}")
            
            if solution:
                success_count += 1
                total_waste += getattr(solution, 'total_waste_fluids', 0)
                total_time += getattr(solution, 'execution_time', 0.0)

        # 複数回実行時のみ統計サマリを追加
        if num_execs > 1:
            self._build_summary(lines, num_execs, success_count, total_waste, total_time)

        with open(os.path.join(directory, "summary.txt"), 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def _build_single_report(self, lines, targets, solution, label):
        lines.append(f"### {label} ###")
        if targets:
            lines.append("  [Targets]")
            for t in targets:
                name = t.name if hasattr(t, 'name') else t.get('name')
                ratios = t.ratios if hasattr(t, 'ratios') else t.get('ratios')
                lines.append(f"    - {name}: {ratios}")
        
        if solution:
            lines.append("  [Results]")
            lines.append(f"    - Mixing Operations   : {len(solution.nodes)}")
            lines.append(f"    - Total Reagents Used : {sum(sum(n.injected_reagent_volumes) for n in solution.nodes)}")
            lines.append(f"    - Total Waste Fluids  : {solution.total_waste_fluids}")
            lines.append(f"    - Execution Time      : {getattr(solution, 'execution_time', 0.0):.4f} s")
        else:
            lines.append("  [Results] No Solution Found.")
        lines.append("-" * 40)

    def _build_summary(self, lines, num_execs, success_count, total_waste, total_time):
        lines.append("")
        lines.append("="*60)
        lines.append(" Statistical Summary ".center(60))
        lines.append("="*60)
        lines.append(f"  Total Executions    : {num_execs}")
        lines.append(f"  Success Rate        : {success_count}/{num_execs} ({success_count/num_execs*100:.1f}%)")
        if success_count > 0:
            lines.append(f"  Avg Waste Fluids    : {total_waste / success_count:.2f}")
            lines.append(f"  Avg Execution Time  : {total_time / success_count:.4f} s")
            lines.append(f"  Total Waste Fluids  : {total_waste}")


class CompareTextExporter(ReportExporter):
    """
    MTWM と提案手法（Extension）の比較結果を並べてテキスト出力する。

    output_data の形式:
        {
            "mtwm":      {"is_success": bool, "solution": OptimizationResult | None},
            "extension": {"is_success": bool, "solution": OptimizationResult | None},
        }
    """

    def export(self, directory: str, input_data: dict, output_data: dict) -> None:
        lines = []
        lines.append("=" * 64)
        lines.append(" MTWM vs Extension  比較レポート ".center(64))
        lines.append("=" * 64)
        lines.append("")

        # ターゲット情報
        targets = input_data.get("targets", [])
        max_mixer_size = input_data.get("max_mixer_size", "?")
        targets_file   = input_data.get("targets_file", "")
        lines.append(f"  Max Mixer Size : {max_mixer_size}")
        if targets_file:
            lines.append(f"  Targets File   : {targets_file}")
        lines.append("")
        lines.append("  [Targets]")
        for t in targets:
            name   = t.name   if hasattr(t, "name")   else t.get("name",   "?")
            ratios = t.ratios if hasattr(t, "ratios") else t.get("ratios", [])
            lines.append(f"    - {name}: {ratios}  (sum={sum(ratios)})")
        lines.append("")

        # 各手法の結果
        mtwm_entry = output_data.get("mtwm", {})
        ext_entry  = output_data.get("extension", {})
        mtwm_sol   = mtwm_entry.get("solution")
        ext_sol    = ext_entry.get("solution")

        lines.append(f"  {'手法':<22} {'廃棄液量':>8}  {'実行時間':>12}  {'状態'}")
        lines.append(f"  {'-'*60}")
        lines.append(self._format_row("MTWM (baseline)", mtwm_sol))
        lines.append(self._format_row("Extension (提案手法)", ext_sol))
        lines.append("")

        # 改善量
        if mtwm_sol and ext_sol:
            diff = mtwm_sol.total_waste_fluids - ext_sol.total_waste_fluids
            pct  = (diff / mtwm_sol.total_waste_fluids * 100
                    if mtwm_sol.total_waste_fluids > 0 else 0.0)
            lines.append(f"  廃棄液削減量  : {diff:+d}  ({pct:+.1f}%)")
            if diff > 0:
                lines.append("  -> 提案手法が優れています [WIN]")
            elif diff == 0:
                lines.append("  -> 同等の結果です [DRAW]")
            else:
                lines.append("  -> MTWM の方が少ない廃棄液でした [MTWM WIN]")
        lines.append("")
        lines.append("=" * 64)

        with open(os.path.join(directory, "compare_report.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def _format_row(label: str, sol: Optional[object]) -> str:
        if sol is None:
            return f"  {label:<22} {'---':>8}  {'---':>12}  NO SOLUTION"
        waste = getattr(sol, "total_waste_fluids", "?")
        t     = getattr(sol, "execution_time", 0.0)
        return f"  {label:<22} {waste:>8}  {t:>10.2f}s  OK"