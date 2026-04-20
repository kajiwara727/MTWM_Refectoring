# main.py
import argparse
from config import get_default_config
from runners import get_runner

def main():
    app_config = get_default_config()
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, help="Runner mode (auto, dfmm, random)")
    args = parser.parse_args()
    
    if args.mode:
        app_config.runner_mode = args.mode
        
    print(f"--- Runner Mode: {app_config.runner_mode.upper()} ---")
    
    try:
        runner = get_runner(app_config.runner_mode, app_config)
        
        # 1. シミュレーションとデータ保存の実行
        result_data = runner.run()
        
        # 2. 結果の可視化 (ランナー自身が描画ロジックを知っている)
        if app_config.visualize_enabled:
            runner.visualize(result_data)
            
        print(f"\n[Finish] 処理が完了しました。データと画像は以下に保存されています:")
        print(f"  -> {result_data.get('session_dir', 'Unknown directory')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()