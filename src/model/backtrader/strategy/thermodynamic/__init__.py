"""
火炉模型计算模块
提供各种参数计算的接口

注意：
- 只提供接口定义，不包含具体实现
- 所有计算函数需要用户自己实现
"""
from model.backtrader.strategy.thermodynamic.chip_peak import (
    ChipPeak,
    ChipPeakCalculator
)
from model.backtrader.strategy.thermodynamic.thermal_params import (
    ThermalParamsCalculator
)
from model.backtrader.strategy.thermodynamic.burn_rate import (
    BurnRateCalculator
)
from model.backtrader.strategy.thermodynamic.signals import (
    SignalChecker
)

__all__ = [
    'ChipPeak',
    'ChipPeakCalculator',
    'ThermalParamsCalculator',
    'BurnRateCalculator',
    'SignalChecker',
]
