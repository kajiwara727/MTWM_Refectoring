import os
from .builders import DFMMGraphBuilder, MTWMProblemGraphBuilder, MTWMResultGraphBuilder
from .renderers import DFMMRenderer, MTWMProblemRenderer, MTWMResultRenderer
from .config import VisualizerConfig

def export_visualization(mode: str, data, filename: str, title: str, config=None):
    """
    データ構造からグラフを構築し、レンダリングして出力する一連の処理を実行します。
    """
    cfg = config or VisualizerConfig
    
    # 出力先ディレクトリの決定
    output_dir = "output/dfmm_plots" if mode == 'dfmm' else "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    # モードに応じた Builder と Renderer の実行
    if mode == 'dfmm':
        builder = DFMMGraphBuilder(cfg)
        G, pos = builder.build(data)
        renderer = DFMMRenderer(G, pos, cfg)
        renderer.render(output_path, title)
        
    elif mode == 'problem':
        builder = MTWMProblemGraphBuilder(cfg)
        G, pos = builder.build(data)
        renderer = MTWMProblemRenderer(G, pos, cfg)
        renderer.render(output_path, title)
        
    elif mode == 'result':
        builder = MTWMResultGraphBuilder(cfg)
        G, pos = builder.build(data)
        renderer = MTWMResultRenderer(G, pos, cfg)
        # Result時のみ、タイトル用に総廃棄液量を渡す
        renderer.render(output_path, title, total_waste=data.total_waste_fluids)
        
    else:
        raise ValueError(f"Unknown visualization mode: '{mode}'")
    
    print(f"  [Visualizing] {title} を出力完了: {output_path}")