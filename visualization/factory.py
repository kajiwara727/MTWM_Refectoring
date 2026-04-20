import os
from .builders import DFMMGraphBuilder, MTWMProblemGraphBuilder, MTWMResultGraphBuilder, ProposedHeuristicGraphBuilder
from .renderers import DFMMRenderer, MTWMProblemRenderer, MTWMResultRenderer, ProposedHeuristicRenderer
from .config import VisualizerConfig

_VISUALIZATION_STRATEGIES = {
    'dfmm': (DFMMGraphBuilder, DFMMRenderer),
    'problem': (MTWMProblemGraphBuilder, MTWMProblemRenderer),
    'result': (MTWMResultGraphBuilder, MTWMResultRenderer),
    'heuristic': (ProposedHeuristicGraphBuilder, ProposedHeuristicRenderer),
}

# ... 以降の export_visualization メソッドは変更なし ...

def export_visualization(mode: str, data, filename: str, title: str, config=None, output_dir=None):
    if mode not in _VISUALIZATION_STRATEGIES:
        raise ValueError(f"Unknown visualization mode: '{mode}'")
        
    BuilderClass, RendererClass = _VISUALIZATION_STRATEGIES[mode]
    cfg = config or VisualizerConfig
    output_dir = output_dir or "output"
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    # グラフの構築とレンダリング
    builder = BuilderClass(cfg)
    G, pos = builder.build(data)
    
    renderer = RendererClass(G, pos, cfg)
    
    # モードに応じた追加パラメータの調整
    kwargs = {'show': False}
    if mode == 'result':
        kwargs['total_waste'] = getattr(data, 'total_waste_fluids', 0)
        
    renderer.render(output_path, title, **kwargs)