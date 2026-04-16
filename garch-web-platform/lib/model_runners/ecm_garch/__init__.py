"""
ECM-GARCH 模型运行器
误差修正 GARCH 模型，考虑长期均衡关系
"""

from .runner import run_ecm_garch

__all__ = ['run_ecm_garch']
