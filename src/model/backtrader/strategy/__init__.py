"""
策略库模块
"""
from model.backtrader.strategy.base import BaseStrategy
from model.backtrader.strategy.thermodynamic import ChipPeak

__all__ = ['BaseStrategy', 'ChipPeak']
