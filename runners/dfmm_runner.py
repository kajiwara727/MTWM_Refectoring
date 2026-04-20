from .base_runner import BaseRunner
from core import build_complete_dfmm_tree
from visualization import export_visualization

class DFMMRunner(BaseRunner):
    def run(self) -> dict:
        targets = self.prepare_targets(self.config.targets)
        tree_structures = {t.name: build_complete_dfmm_tree(t, target_id=idx) for idx, t in enumerate(targets)}

        settings_summary = f"targets{len(targets)}_mixer{self.config.max_mixer_size}"
        session_dir = self.create_session_dir(settings_summary)

        input_data = {"max_mixer_size": self.config.max_mixer_size, "targets": targets}
        output_data = {"status": "success", "message": "DFMM Routing Trees Generated"}
        self.save_reports(session_dir, input_data, output_data)

        return {"targets": targets, "tree_structures": tree_structures, "session_dir": session_dir}

    def visualize(self, result_data: dict) -> None:
        session_dir = result_data["session_dir"]
        if result_data.get("tree_structures"):
            for target_name, tree_nodes in result_data["tree_structures"].items():
                file_name = f"{target_name.replace(' ', '_').lower()}_dfmm.png"
                export_visualization('dfmm', tree_nodes, file_name, f"DFMM Routing Tree: {target_name}", output_dir=session_dir)