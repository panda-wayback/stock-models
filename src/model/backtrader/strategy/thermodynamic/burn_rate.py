"""
燃烧率计算模块
提供筹码燃烧率（卖出权重）的计算接口
"""
from typing import Dict, Optional
from abc import ABC, abstractmethod
from model.backtrader.strategy.thermodynamic.chip_peak import ChipPeak


class BurnRateCalculator(ABC):
    """
    燃烧率计算接口
    
    实现此接口以提供自定义的燃烧率计算算法
    
    根据文档中的差异化抽取逻辑：
    - 获利盘：基础权重高，但受导热系数修正
    - 套牢盘：基础权重低，但恐慌时权重最大化
    """
    
    @abstractmethod
    def calculate(
        self,
        chip_peak: ChipPeak,
        thermal_params: Dict[str, float],
        previous_burn_rate: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        计算燃烧率（筹码卖出权重 - 状态依赖计算）
        
        参数:
        - chip_peak: 筹码峰对象（这就是"燃料"本身）
        - thermal_params: 热力学参数字典
            {
                'temperature': 炉温 T
                'iron_temperature': 铁块温度 VWAP
                'thermal_conductivity': 导热系数 λ
            }
        - previous_burn_rate: 上一个状态的燃烧率（可选，首次计算时为 None）
            {
                'profit_burn_rate': 上一个获利盘燃烧率
                'loss_burn_rate': 上一个套牢盘燃烧率
                'total_burn_rate': 上一个总燃烧率
            }
        
        注意：
        - 燃料 = 筹码峰 = chip_peak.chip_amounts（每个价格区间的筹码量）
        - 燃料不在 thermal_params 中，而是筹码峰本身
        - 每个参数都是根据上一个参数进行计算的（状态依赖）
        
        返回:
        燃烧率字典：
        {
            'profit_burn_rate': 获利盘燃烧率
            'loss_burn_rate': 套牢盘燃烧率
            'total_burn_rate': 总燃烧率
        }
        """
        pass
