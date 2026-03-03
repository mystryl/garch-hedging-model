"""
Models module - GARCH套保模型包装器
提供统一的模型运行接口
"""

from .basic_garch_wrapper import run_model as run_basic_garch
from .dcc_garch_wrapper import run_model as run_dcc_garch
from .ecm_garch_wrapper import run_model as run_ecm_garch

# 模型运行器注册表
MODEL_RUNNERS = {
    'basic_garch': run_basic_garch,
    'dcc_garch': run_dcc_garch,
    'ecm_garch': run_ecm_garch
}

__all__ = [
    'run_basic_garch',
    'run_dcc_garch',
    'run_ecm_garch',
    'MODEL_RUNNERS'
]
