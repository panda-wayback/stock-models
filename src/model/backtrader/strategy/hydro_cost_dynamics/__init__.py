"""
HCD (Hydro-Cost Dynamics) 量化模型
基于"物理做功"原理的资金流向分析系统

核心概念：
- 通过计算资金能流 (Money Energy Flow, MEF) 来量化主力资金的"注水"与"抽水"行为
- 基于物理学公式：做功 = 力 × 位移
- 力 = 成交量，位移 = 涨跌幅

模块结构：
- hcd_model.py: HCD 模型核心类，提供指标计算和信号生成
- hcd_strategy.py: HCD 交易策略类，用于 Backtrader 回测
"""
from model.backtrader.strategy.hydro_cost_dynamics.hcd_model import HCDModel
from model.backtrader.strategy.hydro_cost_dynamics.hcd_strategy import HCDStrategy

__all__ = [
    'HCDModel',
    'HCDStrategy',
]