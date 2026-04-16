import argparse
from config import get_default_config
from runners import get_runner
from visualization import export_visualization

def main():
    app_config = get_default_config()
    
    # 拡張性：コマンドライン引数でモード指定可能に
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, help="Runner mode (auto, dfmm)")
    args = parser.parse_args()
    
    if args.mode:
        app_config.runner_mode = args.mode
        
    print(f"--- Runner Mode: {app_config.runner_mode.upper()} ---")
    
    try:
        runner = get_runner(app_config.runner_mode, app_config)
        result = runner.run()
        
        # モードごとの可視化振り分け
        if app_config.runner_mode == "auto" and result.get("solution"):
            export_visualization('problem', result["problem"], "mtwm_problem_structure.png", "MTWM Problem Structure")
            export_visualization('result', result["solution"], "mtwm_optimized_result.png", "MTWM Optimized Result")
            
        elif app_config.runner_mode == "dfmm" and result.get("tree_structures"):
            for target_name, tree_nodes in result["tree_structures"].items():
                file_name = f"{target_name.replace(' ', '_').lower()}_dfmm.png"
                export_visualization('dfmm', tree_nodes, file_name, f"DFMM Routing Tree: {target_name}")
        
        print("\n[Finish] すべての工程が正常に完了しました。")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()