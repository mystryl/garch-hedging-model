"""
Models module - GARCH套保模型包装器

重构说明：
- 使用新的 lib.model_runners 模块
- 简洁直接的模型调用接口
- 统一的返回格式
"""

# 添加 lib 目录到路径
import sys
from pathlib import Path
lib_dir = Path(__file__).parent.parent / 'lib'
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from lib.model_runners.basic_garch import run_basic_garch

# 模型运行器注册表
MODEL_RUNNERS = {
    'basic_garch': run_basic_garch,
    # TODO: 添加其他模型
    # 'dcc_garch': run_dcc_garch,
    # 'ecm_garch': run_ecm_garch
}

__all__ = [
    'run_basic_garch',
    'MODEL_RUNNERS'
]
