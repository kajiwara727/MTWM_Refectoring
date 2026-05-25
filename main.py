# main.py
"""
MTWM / 提案手法 実行エントリーポイント。

使い方:
  python main.py                              # config.py の設定を 1 回実行
  python main.py --mode compare               # MTWM vs Extension を 1 回比較
  python main.py --mode compare --repeat 10   # ランダム生成して 10 回比較

  # 保存済みターゲットを指定して実行
  python main.py --from-file path/to/targets.json --mode auto
  python main.py --from-file path/to/targets.json --mode compare
  python main.py --from-file path/to/targets.json --mode compare --repeat 3

  # ディレクトリを指定 → 内部の targets.json を全部一括実行
  python main.py --from-file output/random/session_dir/ --mode compare

  python main.py --paper-example              # 論文 Fig.5/6 の例題

オプション:
  --mode        実行モード (auto / dfmm / random / extension / compare)
  --from-file   targets.json ファイルまたはディレクトリのパス
  --repeat N    同じターゲットを N 回繰り返す（--from-file がディレクトリの場合は無視）
  --no-visualize PNG 出力をスキップ（高速化）
"""

import argparse
import copy
from pathlib import Path
from typing import List, Optional

from config import get_default_config, get_paper_example_config
from runners import get_runner


# ──────────────────────────────────────────────────────────────
# ヘルパー: 実行対象ファイルリストの収集
# ──────────────────────────────────────────────────────────────

def collect_target_files(from_file: Optional[str], repeat: int) -> List[Optional[str]]:
    """
    --from-file と --repeat の組み合わせから実行対象ファイルリストを作る。

    Returns:
        [None, None, ...]          → ファイルなし（config使用）× repeat 回
        [file, file, ...]          → 同一ファイル × repeat 回
        [file1, file2, ...]        → ディレクトリ内の全 targets.json（repeat は無視）
    """
    if from_file is None:
        # ファイル指定なし: config.targets を repeat 回使う
        return [None] * repeat

    path = Path(from_file)

    if path.is_file():
        # 単一ファイル: repeat 回繰り返す
        return [str(path)] * repeat

    if path.is_dir():
        # ディレクトリ: 再帰的に targets.json を全収集
        files = sorted(path.rglob("targets.json"))
        if not files:
            raise FileNotFoundError(
                f"targets.json が見つかりません: {from_file}\n"
                f"  hint: random モードを先に実行すると exec_N/targets.json が生成されます。"
            )
        print(f"[--from-file] ディレクトリ内の targets.json を {len(files)} 件検出")
        return [str(f) for f in files]

    raise FileNotFoundError(f"ファイルまたはディレクトリが見つかりません: {from_file}")


# ──────────────────────────────────────────────────────────────
# 1 回分の実行
# ──────────────────────────────────────────────────────────────

def run_once(app_config, targets_file: Optional[str], trial_no: int, total: int) -> dict:
    """
    targets_file（または config.targets）を使って 1 回実行する。
    """
    from core.io.targets_io import load_targets

    cfg = copy.deepcopy(app_config)   # 各試行で独立したコピー

    # ── ターゲット上書き ────────────────────────────────────────
    if targets_file is not None:
        targets, max_mixer_size, meta = load_targets(targets_file)
        cfg.targets        = targets
        cfg.max_mixer_size = max_mixer_size

        label = (f"source={meta.get('source','?')}, "
                 f"created_at={meta.get('created_at','?')[:19]}")
    else:
        label = "config.targets を使用"

    # ── ヘッダ表示 ──────────────────────────────────────────────
    print(f"\n{'#'*56}")
    print(f"  Trial {trial_no}/{total}  ({label})")
    print(f"  Mode: {cfg.runner_mode.upper()}  |  Max Mixer: {cfg.max_mixer_size}")
    if targets_file:
        print(f"  File: {targets_file}")
    print(f"{'#'*56}\n")

    runner      = get_runner(cfg.runner_mode, cfg)
    result_data = runner.run()

    if cfg.visualize_enabled:
        runner.visualize(result_data)

    return result_data


# ──────────────────────────────────────────────────────────────
# バッチ完了サマリ
# ──────────────────────────────────────────────────────────────

def print_batch_summary(results: list, mode: str) -> None:
    """N 回実行後の統計サマリを標準出力に表示する"""
    n = len(results)
    if n <= 1:
        return

    print(f"\n{'='*64}")
    print(f"  バッチ実行完了  ({n} trials, mode={mode})".center(64))
    print(f"{'='*64}")

    if mode == "compare":
        mtwm_wastes = []
        ext_wastes  = []
        for r in results:
            ms = r.get("mtwm_solution")
            es = r.get("extension_solution")
            if ms:
                mtwm_wastes.append(ms.total_waste_fluids)
            if es:
                ext_wastes.append(es.total_waste_fluids)

        if mtwm_wastes:
            print(f"  MTWM   waste : avg={sum(mtwm_wastes)/len(mtwm_wastes):.2f}  "
                  f"min={min(mtwm_wastes)}  max={max(mtwm_wastes)}  "
                  f"total={sum(mtwm_wastes)}")
        if ext_wastes:
            print(f"  Ext    waste : avg={sum(ext_wastes)/len(ext_wastes):.2f}  "
                  f"min={min(ext_wastes)}  max={max(ext_wastes)}  "
                  f"total={sum(ext_wastes)}")
        if mtwm_wastes and ext_wastes and len(mtwm_wastes) == len(ext_wastes):
            diffs = [m - e for m, e in zip(mtwm_wastes, ext_wastes)]
            wins  = sum(1 for d in diffs if d > 0)
            draws = sum(1 for d in diffs if d == 0)
            loses = sum(1 for d in diffs if d < 0)
            avg_reduction = sum(diffs) / len(diffs)
            print(f"  削減量(avg)  : {avg_reduction:+.2f}")
            print(f"  提案手法 勝/引/負 : {wins}/{draws}/{loses}")

    else:
        wastes = []
        times  = []
        for r in results:
            sol = r.get("solution")
            if sol:
                wastes.append(sol.total_waste_fluids)
                times.append(sol.execution_time)
        if wastes:
            print(f"  waste  : avg={sum(wastes)/len(wastes):.2f}  "
                  f"min={min(wastes)}  max={max(wastes)}")
        if times:
            print(f"  time   : avg={sum(times)/len(times):.2f}s  "
                  f"min={min(times):.2f}s  max={max(times):.2f}s")
        print(f"  成功率  : {len(wastes)}/{n}")

    print(f"{'='*64}\n")


# ──────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MTWM / Proposed Extension-Node Method Runner",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["auto", "dfmm", "random", "proposed", "extension", "compare"],
        help=(
            "実行モードを選択:\n"
            "  auto      : MTWM（ベースライン）\n"
            "  dfmm      : 純粋 DFMM\n"
            "  random    : ランダム実験（targets.json を自動保存）\n"
            "  proposed  : 試作提案手法（最多試薬フィルタ）\n"
            "  extension : 【提案手法】拡張ノード導入\n"
            "  compare   : 同一ターゲットで MTWM vs Extension を比較"
        ),
    )
    parser.add_argument(
        "--from-file",
        type=str,
        metavar="PATH",
        help=(
            "targets.json ファイル または ディレクトリ を指定。\n"
            "  ファイル指定: そのターゲットで実行（--repeat N で N 回繰り返し）\n"
            "  ディレクトリ指定: 内部の targets.json を全て一括実行\n"
            "例:\n"
            "  --from-file output/random/.../exec_1/targets.json\n"
            "  --from-file output/random/session_dir/"
        ),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        help=(
            "同じターゲット（または config.targets）を N 回繰り返す。\n"
            "--from-file にディレクトリを指定した場合は無視される。\n"
            "例: --mode compare --repeat 10"
        ),
    )
    parser.add_argument(
        "--paper-example",
        action="store_true",
        help="論文 Fig.5/6 の例題（15:1:2 / 8:1:9 / 1:8:9 / M=5）を extension モードで実行",
    )
    parser.add_argument(
        "--no-visualize",
        action="store_true",
        help="可視化（PNG 出力）をスキップ（高速化）",
    )
    args = parser.parse_args()

    # ── ベース設定の選択 ────────────────────────────────────────
    if args.paper_example:
        app_config = get_paper_example_config()
        print("=== 論文例題モード: 15:1:2 / 8:1:9 / 1:8:9  (M=5) ===")
    else:
        app_config = get_default_config()

    if args.mode:
        app_config.runner_mode = args.mode

    if args.no_visualize:
        app_config.visualize_enabled = False

    # ── 実行対象ファイルリストを作成 ────────────────────────────
    try:
        target_files = collect_target_files(args.from_file, args.repeat)
    except (FileNotFoundError, ValueError) as e:
        print(f"\n[Error] {e}")
        return

    total = len(target_files)

    print(f"\n{'='*56}")
    print(f"  Runner Mode : {app_config.runner_mode.upper()}")
    print(f"  Max Mixer   : {app_config.max_mixer_size}")
    print(f"  Total Trials: {total}")
    if args.from_file:
        print(f"  From        : {args.from_file}")
    print(f"{'='*56}")

    # ── N 回ループ ────────────────────────────────────────────
    all_results = []
    for i, targets_file in enumerate(target_files, start=1):
        try:
            result = run_once(app_config, targets_file, trial_no=i, total=total)
            all_results.append(result)

            # 出力先を表示
            print(f"\n[Trial {i}/{total} 完了]")
            print(f"  -> {result.get('session_dir', 'Unknown')}")
            if "targets_file" in result:
                print(f"  -> targets.json: {result['targets_file']}")

        except Exception as e:
            import traceback
            print(f"\n[Trial {i}/{total} Error] {e}")
            traceback.print_exc()

    # ── バッチサマリ ──────────────────────────────────────────
    print_batch_summary(all_results, app_config.runner_mode)

    print(f"[Finish] 全 {len(all_results)}/{total} 試行完了")


if __name__ == "__main__":
    main()
