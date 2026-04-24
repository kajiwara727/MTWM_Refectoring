import json
import os
from abc import ABC, abstractmethod
from utils.io_manager import MTWMEncoder

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