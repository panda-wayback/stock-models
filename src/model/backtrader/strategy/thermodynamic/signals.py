"""
信号判定模块
提供买入、持有、卖出信号的判定接口
"""
from typing import Dict
from abc import ABC, abstractmethod
from model.backtrader.strategy.thermodynamic.chip_peak import ChipPeak


class SignalChecker(ABC):
    """
    信号判定接口
    
    实现此接口以提供自定义的信号判定算法
    """
    
    @abstractmethod
    def check_ignition(
        self,
        chip_peak: ChipPeak,
        thermal_params: Dict[str, float],
        burn_rate: Dict[str, float]
    ) -> bool:
        """
        检查买入信号（引燃点）
        
        条件（根据文档）：
        - 底部筹码峰厚实（有庄）
        - 导热系数正常/偏高
        - 股价突破新平台
        
        参数:
        - chip_peak: 筹码峰对象
        - thermal_params: 热力学参数
        - burn_rate: 燃烧率
        
        返回:
        True: 买入信号
        False: 无买入信号
        """
        pass
    
    @abstractmethod
    def check_hold(
        self,
        chip_peak: ChipPeak,
        thermal_params: Dict[str, float],
        burn_rate: Dict[str, float]
    ) -> bool:
        """
        检查持有信号（空中加油）
        
        条件（根据文档）：
        - 底部筹码逐渐转移至中部，形成新的坚实筹码峰（多级火箭）
        
        参数:
        - chip_peak: 筹码峰对象
        - thermal_params: 热力学参数
        - burn_rate: 燃烧率
        
        返回:
        True: 继续持有
        False: 考虑卖出
        """
        pass
    
    @abstractmethod
    def check_burnout(
        self,
        chip_peak: ChipPeak,
        thermal_params: Dict[str, float],
        burn_rate: Dict[str, float]
    ) -> bool:
        """
        检查卖出信号（燃料耗尽）
        
        条件（根据文档）：
        - 底部筹码峰归零（被算光了）
        - 顶部堆积巨量
        - 导热系数值恶化
        
        参数:
        - chip_peak: 筹码峰对象
        - thermal_params: 热力学参数
        - burn_rate: 燃烧率
        
        返回:
        True: 卖出信号
        False: 无卖出信号
        """
        pass
