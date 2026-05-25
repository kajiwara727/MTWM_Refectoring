# MTWM / 提案手法（拡張ノード）実験フレームワーク

MEDA（Microelectrode-dot-array）バイオチップ上での多目標サンプル調製において、  
廃棄液を最小化する **MTWM（Multi-Target Waste Minimization）** と、  
それを改善する **提案手法（拡張ノード導入）** の実装・比較実験フレームワーク。

---

## 目次

1. [概要](#概要)
2. [必要環境](#必要環境)
3. [ディレクトリ構成](#ディレクトリ構成)
4. [クイックスタート](#クイックスタート)
5. [実行モード](#実行モード)
6. [コマンドライン引数](#コマンドライン引数)
7. [config.py による設定](#configpy-による設定)
8. [比較実験ワークフロー](#比較実験ワークフロー)
9. [出力ファイル](#出力ファイル)
10. [ソルバー設定](#ソルバー設定)
11. [アルゴリズム概要](#アルゴリズム概要)

---

## 概要

| 手法 | 説明 |
|---|---|
| **DFMM** | Division-by-Factor Method for MEDA。ヒューリスティックで混合ツリーを構築 |
| **MTWM** | スケルトンツリーを基に CP-SAT で廃棄液を最小化（ベースライン） |
| **提案手法** | 拡張ノード `u_{p,h}` を導入し、MTWM より廃棄液を削減（論文提案） |

---

## 必要環境

```
Python 3.10 以上
ortools（CP-SAT ソルバー）
matplotlib（可視化）
networkx（グラフ構築）
```

インストール:

```bash
pip install ortools matplotlib networkx
```

---

## ディレクトリ構成

```
MTWM_Refactoring/
│
├── main.py                        # 実行エントリーポイント
├── config.py                      # ターゲット・モードの設定
│
├── core/
│   ├── models.py                  # データクラス定義
│   ├── algorithm/
│   │   ├── dfmm.py                # DFMM ツリー構築・因数分解
│   │   └── extension.py           # 拡張ノード生成ロジック（提案手法）
│   ├── solver/
│   │   ├── problem.py             # MTWMProblem（問題定義）
│   │   ├── extension_problem.py   # ExtensionMTWMProblem（拡張ノード込み）
│   │   ├── solver.py              # MTWMSolver（CP-SAT）
│   │   ├── extension_solver.py    # ExtensionMTWMSolver（提案手法）
│   │   ├── solver_config.py       # ソルバーチューニングパラメータ
│   │   └── dto.py                 # 結果格納データクラス
│   └── io/
│       └── targets_io.py          # ターゲット設定の保存・読み込み
│
├── runners/
│   ├── standard_runner.py         # MTWM 実行ランナー
│   ├── extension_runner.py        # 提案手法 実行ランナー
│   ├── compare_runner.py          # 比較実験ランナー（MTWM vs 提案手法）
│   ├── random_runner.py           # ランダム実験ランナー
│   ├── dfmm_runner.py             # 純粋 DFMM ランナー
│   └── factory.py                 # モード名 → ランナーのルーティング
│
├── visualization/                 # グラフ描画（PNG 出力）
├── utils/                         # IO・レポート出力ユーティリティ
│
└── output/                        # 実行結果の出力先（自動生成）
    ├── auto/                      # MTWM の結果
    ├── extension/                 # 提案手法の結果
    ├── compare/                   # 比較実験の結果
    └── random/                    # ランダム実験の結果
```

---

## クイックスタート

```bash
# 論文の例題（15:1:2 / 8:1:9 / 1:8:9、M=5）で MTWM vs 提案手法を比較
python main.py --paper-example

# config.py のターゲットで MTWM を実行
python main.py --mode auto

# config.py のターゲットで提案手法を実行
python main.py --mode extension

# MTWM と提案手法を同じターゲットで実行して比較
python main.py --mode compare
```

---

## 実行モード

| モード | 説明 |
|---|---|
| `auto` | MTWM（スケルトンツリー + CP-SAT 廃棄液最小化） |
| `extension` | 提案手法（拡張ノード導入による廃棄液削減） |
| `compare` | 同一ターゲットで MTWM と提案手法を両方実行して比較 |
| `random` | ランダムターゲットで多数試行（`targets.json` を自動保存） |
| `dfmm` | 純粋 DFMM（ヒューリスティックのみ、最適化なし） |

---

## コマンドライン引数

```
python main.py [--mode MODE] [--from-file PATH] [--repeat N]
               [--paper-example] [--no-visualize]
```

### `--mode MODE`

実行モードを指定する。`config.py` の `runner_mode` より優先される。

```bash
python main.py --mode compare
python main.py --mode auto
python main.py --mode extension
```

---

### `--from-file PATH`

保存済みの `targets.json` ファイルまたはディレクトリを指定する。  
指定した設定を `config.py` の `targets` より優先して使用する。

**ファイルを指定した場合:**  
そのターゲット設定を読み込んで 1 回実行する（`--repeat` で繰り返し可）。

```bash
python main.py --from-file output/random/.../exec_3/targets.json --mode compare
```

**ディレクトリを指定した場合:**  
ディレクトリ内の `targets.json` を全て自動検索し、順番に実行する（`--repeat` は無視）。

```bash
# ランダム実験で溜まったターゲットを全て比較
python main.py --from-file output/random/targets3_reagents3_sum20_mixer5/20260525_xxx/ --mode compare
```

---

### `--repeat N`

同じターゲット（またはランダム生成）を N 回繰り返す。  
`--from-file` にディレクトリを指定した場合は無視される。

```bash
# ランダム生成して 10 回比較（統計的評価）
python main.py --mode compare --repeat 10

# 同じターゲットで 3 回実行（実行時間のばらつき確認）
python main.py --from-file targets.json --mode auto --repeat 3
```

---

### `--paper-example`

論文 Fig.5・Fig.6 の例題で実行する。

- ターゲット: `15:1:2`、`8:1:9`、`1:8:9`
- M（最大ミキサーサイズ）: 5
- モード: `extension`（`--mode` で上書き可）

```bash
python main.py --paper-example
python main.py --paper-example --mode compare  # 比較モードで論文例題を実行
```

---

### `--no-visualize`

PNG 画像の出力をスキップする。ソルバーのみ実行するため高速。

```bash
python main.py --mode compare --repeat 20 --no-visualize
```

---

## config.py による設定

`main.py` を引数なしで実行したとき、`config.py` の `get_default_config()` が使われる。

```python
# config.py
def get_default_config() -> MTWMConfig:
    return MTWMConfig(
        runner_mode="auto",       # 実行モード（"auto" / "extension" / "compare" / "random" / "dfmm"）
        max_mixer_size=5,         # 最大ミキサーサイズ M（拡張ノードの生成に影響）
        targets=[
            Target(name='Target 1', ratios=[15, 1, 2]),
            Target(name='Target 2', ratios=[8,  1, 9]),
            Target(name='Target 3', ratios=[1,  8, 9]),
        ],
        random_config=RandomConfig(
            num_targets=3,        # 1 試行あたりのターゲット数
            num_reagents=3,       # 試薬の種類数
            ratio_sum=20,         # 比率の合計（例: 20 → [3,9,8] など）
            num_executions=20,    # 試行回数（random モードのみ使用）
        ),
    )
```

### `max_mixer_size` の影響

- この値より `droplet_weight` が大きいノードが**拡張ノードの候補**になる
- 小さくすると拡張ノードが増え、廃棄削減効果が上がる可能性があるが計算時間も増える

---

## 比較実験ワークフロー

### ワークフロー A：一括比較（最もシンプル）

```bash
python main.py --mode compare --repeat 20 --no-visualize
```

20 回ランダムターゲットを生成して MTWM vs 提案手法を比較し、  
最後にバッチサマリを表示する。

```
================================================================
  バッチ実行完了  (20 trials, mode=compare)
================================================================
  MTWM   waste : avg=6.40  min=3  max=12  total=128
  Ext    waste : avg=3.80  min=1  max=8   total=76
  削減量(avg)  : +2.60
  提案手法 勝/引/負 : 16/2/2
================================================================
```

---

### ワークフロー B：ランダム実験 → 後から比較

```bash
# Step 1: ランダム実験を実行（各試行の targets.json が保存される）
python main.py --mode random

# Step 2: 保存された全ターゲットを使ってまとめて比較
python main.py --from-file output/random/session_dir/ --mode compare --no-visualize
```

---

### ワークフロー C：特定試行のみ深掘り

```bash
# 気になった試行を個別に MTWM と提案手法それぞれで実行
python main.py --from-file output/random/.../exec_5/targets.json --mode auto
python main.py --from-file output/random/.../exec_5/targets.json --mode extension
python main.py --from-file output/random/.../exec_5/targets.json --mode compare
```

---

## 出力ファイル

実行ごとにタイムスタンプ付きのディレクトリが `output/` 以下に作成される。

```
output/{mode}/{設定サマリ}/{YYYYMMDD_HHmmss}/
```

### 共通ファイル

| ファイル | 内容 |
|---|---|
| `targets.json` | ターゲット設定（`--from-file` で再利用可能） |
| `input.json` | 入力データ（JSON 形式） |
| `output.json` | 出力データ・最適化結果（JSON 形式） |
| `summary.txt` | テキスト形式のレポート |
| `*.png` | 可視化グラフ（`--no-visualize` で省略可） |

### compare モードの追加ファイル

| ファイル | 内容 |
|---|---|
| `compare_report.txt` | MTWM vs 提案手法の並列比較表 |

### random モードのディレクトリ構造

```
output/random/targets3_reagents3_sum20_mixer5/{timestamp}/
  exec_1/targets.json      ← 試行 1 のターゲット設定
  exec_2/targets.json      ← 試行 2 のターゲット設定
  ...
  exec_N/targets.json
  exec_1_result.png
  input.json
  output.json
  summary.txt
```

### targets.json の形式

```json
{
  "max_mixer_size": 5,
  "source": "random",
  "created_at": "2026-05-25T21:30:00.123456",
  "num_targets": 3,
  "num_reagents": 3,
  "targets": [
    {"name": "Target_1", "ratios": [3, 9, 8]},
    {"name": "Target_2", "ratios": [7, 4, 9]},
    {"name": "Target_3", "ratios": [11, 2, 7]}
  ]
}
```

---

## ソルバー設定

`core/solver/solver_config.py` の `SolverConfig` でチューニングできる。  
問題規模に応じてランナーが自動選択する。

### プリセット一覧

| プリセット | workers | 時間制限 | 用途 |
|---|---|---|---|
| `small()` | 4 | 60 s | 動作確認・小規模 |
| `default_mtwm()` | 8 | 5000 s | MTWM 中規模 |
| `large_mtwm()` | 16 | 5000 s | MTWM 大規模（ノード数 > 80） |
| `default_extension()` | 16 | 5000 s | 提案手法 中規模 |
| `large_extension()` | 16 | 5000 s | 提案手法 大規模（ノード数 > 80） |
| `fast_feasibility()` | 16 | 300 s | とにかく速く解を得たいとき |

### 自動選択ロジック

```
ノード数 > 80 または 拡張ノード数 > 20
  → large_* を使用
それ以外
  → default_* を使用
```

### 手動でプリセットを指定する場合

```python
from core.solver.solver import MTWMSolver
from core.solver.solver_config import SolverConfig

solver = MTWMSolver(problem, solver_config=SolverConfig.fast_feasibility())
```

---

## アルゴリズム概要

### DFMM（Division-by-Factor Method for MEDA）

目標比率の合計を最大ミキサーサイズ以下の因数に分解し、再帰的に混合ツリーを構築するヒューリスティック。各ノードへの試薬注入量（`reagent_dispensations`）をここで決定し、CP-SAT の初期解ヒントとして使用する。

### MTWM（Multi-Target Waste Minimization）

複数ターゲット間でノードを共有（シェアリングエッジ `w`）することで廃棄液を削減する整数計画問題。CP-SAT（OR-Tools）で解く。

**目的関数:**

```
Minimize Σ waste_fluids(node)
```

### 提案手法（拡張ノード）

重み `p > M` の中間ノードを 2 つずつペアにして **拡張ノード** `u_{p,h}` を生成。拡張ノードは 1:1 混合で同じ重みの液滴を生成し、下流ノードに供給できる。これにより MTWM では実現できなかった共有経路が追加され、廃棄液がさらに削減される。

**拡張ノード変数（論文 eq.10〜13）:**

| 変数 | 説明 |
|---|---|
| `C^k_{p,h}` | 拡張ノードの試薬 k の濃度 |
| `is_active_{p,h}` | アクティブフラグ（BoolVar） |
| `z^{m,l,i}_{p,h}` | 拡張ノード → 通常ノードへのフロー（BoolVar） |
| `waste_{p,h}` | 廃棄液量 = `2 * is_active - Σz` |

### ソルバーチューニングの要点

| 設定 | 効果 |
|---|---|
| `linearization_level = 2` | LP 緩和を有効化（最重要。0 にすると極端に遅くなる） |
| `linearize_products = True` | `w*R` 積を二値展開で完全線形化し LP 緩和を tight にする |
| `z` を BoolVar 化 | `z*C` 積を `OnlyEnforceIf` で線形化（拡張手法のみ） |
| `use_dfmm_hints = True` | DFMM の結果を初期解ヒントとして登録し上界を早期確定 |
