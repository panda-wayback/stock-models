"""
量化交易模型框架

支持多种回测框架：
- Backtrader: 基于 Backtrader 的回测框架
- VnPy: 基于 VnPy 的框架（待实现）
"""
from model import backtrader

__all__ = ['backtrader']
