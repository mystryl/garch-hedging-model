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
from lib.model_runners.dcc_garch import run_dcc_garch
from lib.model_runners.ecm_garch import run_ecm_garch
from lib.model_runners.spread_arbitrage import run_spread_arbitrage

# 模型运行器注册表
MODEL_RUNNERS = {
    'basic_garch': run_basic_garch,
    'dcc_garch': run_dcc_garch,
    'ecm_garch': run_ecm_garch,
    'spread_arbitrage': run_spread_arbitrage
}

__all__ = [
    'run_basic_garch',
    'run_dcc_garch',
    'run_ecm_garch',
    'run_spread_arbitrage',
    'MODEL_RUNNERS'
]
