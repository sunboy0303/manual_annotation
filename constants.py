import numpy as np

DEFAULT_DESCRIPTOR = np.zeros(128, dtype=np.float32)
DEFAULT_SCALE = 30.0
DEFAULT_ANGLE = 0.0
DEFAULT_ZOOM = 2.0
MIN_ZOOM = 0.1
MAX_ZOOM = 100.0  # 最大支持100倍放大，配合0.01精度
