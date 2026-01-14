"""
策略库模块
"""
from model.backtrader.strategy.base import BaseStrategy
from model.backtrader.strategy.hydro_cost_dynamics import HCDStrategy

__all__ = ['BaseStrategy', 'HCDStrategy']
