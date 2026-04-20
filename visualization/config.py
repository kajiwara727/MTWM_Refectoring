import matplotlib.cm as cm

class VisualizerConfig:
    # 共通設定
    NODE_SIZE = 1500
    FONT_SIZE = 8
    ARROW_SIZE = 15
    
    # 座標の間隔設定
    X_SPACING_TARGET = 4.0
    X_SPACING_NODE = 1.2
    
    # MTWM結果可視化用の設定
    RESULT_NODE_SIZE = 3000
    REAGENT_NODE_SIZE = 800
    STATE_FONT_SIZE = 8
    Y_OFFSET_STATE = 0.15  # ← 0.3 から 0.15 に変更して空白を詰める
    Y_OFFSET_REAGENT = -0.5
    VOLUME_CMAP = cm.viridis