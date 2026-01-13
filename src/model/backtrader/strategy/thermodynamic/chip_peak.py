"""
筹码峰计算模块
提供筹码峰（燃料）数据结构和计算接口

核心概念：
- 燃料 = 筹码峰：动态演变的筹码分布，是驱动筹码发生物理位移的动能
- 筹码峰不再是静态的，而是随交易行为动态演变的函数
"""
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import pandas as pd


class ChipPeak:
    """
    筹码峰（燃料）数据结构
    
    存储不同价格区间的筹码分布，用于分析主力资金的真实意图
    
    核心概念：
    - 燃料 = 筹码峰：动态演变的筹码分布
    - 能量源：驱动筹码发生物理位移的动能
    - 筹码分布不再是静态的，而是随交易行为动态演变的函数
    """
    
    def __init__(
        self,
        price_levels: List[float],
        chip_amounts: List[float],
        current_price: float,
        vwap: float,
        total_volume: float,
        thermal_conductivity: float
    ):
        """
        初始化筹码峰（燃料）
        
        参数:
        - price_levels: 价格区间列表（从小到大）
        - chip_amounts: 每个价格区间对应的筹码量（与price_levels一一对应）
          这就是"燃料"本身 - 动态演变的筹码分布
        - current_price: 当前股价（炉温 T）
        - vwap: 成交均价（铁块温度）
        - total_volume: 总成交量（用于计算，但燃料是筹码分布本身）
        - thermal_conductivity: 导热系数 λ
        
        注意：
        - 燃料 = 筹码峰 = chip_amounts（每个价格区间的筹码量）
        - 这是驱动筹码发生物理位移的动能
        """
        self.price_levels = price_levels
        self.chip_amounts = chip_amounts
        self.current_price = current_price
        self.vwap = vwap
        self.total_volume = total_volume
        self.thermal_conductivity = thermal_conductivity
        
        # 计算衍生指标
        self._calculate_derived_metrics()
    
    def _calculate_derived_metrics(self):
        """计算衍生指标"""
        if not self.price_levels or not self.chip_amounts:
            self.peak_price = self.current_price
            self.peak_amount = 0.0
            self.avg_cost = self.vwap
            self.profit_ratio = 0.0
            self.loss_ratio = 0.0
            return
        
        # 找到峰值位置（筹码量最大的价格区间）
        max_idx = max(range(len(self.chip_amounts)), key=lambda i: self.chip_amounts[i])
        self.peak_price = self.price_levels[max_idx]
        self.peak_amount = self.chip_amounts[max_idx]
        
        # 计算平均持仓成本
        total_chips = sum(self.chip_amounts)
        if total_chips > 0:
            weighted_sum = sum(p * a for p, a in zip(self.price_levels, self.chip_amounts))
            self.avg_cost = weighted_sum / total_chips
        else:
            self.avg_cost = self.vwap
        
        # 计算获利盘和套牢盘比例
        profit_chips = sum(
            amount for price, amount in zip(self.price_levels, self.chip_amounts)
            if price < self.current_price
        )
        loss_chips = sum(
            amount for price, amount in zip(self.price_levels, self.chip_amounts)
            if price > self.current_price
        )
        
        total_chips = profit_chips + loss_chips
        if total_chips > 0:
            self.profit_ratio = profit_chips / total_chips
            self.loss_ratio = loss_chips / total_chips
        else:
            self.profit_ratio = 0.0
            self.loss_ratio = 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典格式（便于存储）"""
        return {
            'price_levels': self.price_levels,
            'chip_amounts': self.chip_amounts,
            'current_price': self.current_price,
            'vwap': self.vwap,
            'total_volume': self.total_volume,
            'thermal_conductivity': self.thermal_conductivity,
            'peak_price': self.peak_price,
            'peak_amount': self.peak_amount,
            'avg_cost': self.avg_cost,
            'profit_ratio': self.profit_ratio,
            'loss_ratio': self.loss_ratio,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChipPeak':
        """从字典恢复筹码峰对象"""
        return cls(
            price_levels=data['price_levels'],
            chip_amounts=data['chip_amounts'],
            current_price=data['current_price'],
            vwap=data['vwap'],
            total_volume=data['total_volume'],
            thermal_conductivity=data['thermal_conductivity']
        )


class ChipPeakCalculator(ABC):
    """
    筹码峰计算接口
    
    实现此接口以提供自定义的筹码峰计算算法
    
    注意：
    - 此接口主要用于在 ThermalParamsCalculator 内部计算筹码峰
    - 筹码峰（燃料）是热力学参数的一部分
    - 每个参数都是根据上一个参数进行计算的（状态依赖）
    """
    
    @abstractmethod
    def calculate(
        self,
        df: pd.DataFrame,
        thermal_params: Dict[str, float],
        previous_chip_peak: Optional[ChipPeak] = None,
        price_step: float = 0.01
    ) -> ChipPeak:
        """
        计算筹码峰（状态依赖计算）
        
        参数:
        - df: 完整历史数据 DataFrame（包含 open, high, low, close, volume）
            - 传入所有可用的历史数据
            - 计算函数内部按需使用（可以使用最近1天、2天、3天等）
        - thermal_params: 热力学参数字典（基础参数，不包含筹码峰）
            {
                'temperature': 炉温 T（当前股价）
                'iron_temperature': 铁块温度 VWAP（成交均价）
                'thermal_conductivity': 导热系数 λ
            }
        - previous_chip_peak: 上一个状态的筹码峰（可选，首次计算时为 None）
        - price_step: 价格步长
            作用：每个价格区间的宽度（单位：元）
            例如：
                - price_step=0.01 表示每个区间代表0.01元（一分钱）
                - price_step=0.1 表示每个区间代表0.1元（一毛钱）
                - price_step=0.5 表示每个区间代表0.5元（五毛钱）
                - price_step=1.0 表示每个区间代表1.0元（一块钱）
            说明：
                - 价格区间是动态的，根据价格范围和 price_step 自动计算区间数量
                - 例如：价格范围 4.5-5.5，price_step=0.01，则会有100个区间
                - 每个区间对应一个价格点（区间中心）和一个筹码量
            推荐值：
                - 低价股（<10元）：price_step=0.01（一分钱，默认值）
                - 中价股（10-50元）：price_step=0.01 或 0.1
                - 高价股（>50元）：price_step=0.1 或 0.5
            注意：
                - 默认值 0.01（一分钱）适合大多数A股
                - 对于5块钱的股票，0.01（一分钱）比0.1（一毛钱）更合适
        
        返回:
        ChipPeak 对象（当前状态的筹码峰）
        
        计算方式推荐（区间合并法）：
        ============================================
        推荐使用"价格步长 + 区间合并"的方式，这是最精确的计算方法：
        
        1. 使用 price_step 定义细粒度价格区间（如 0.01元一个区间）
        2. 对于每个K线，将其成交量按比例分配到 [low, high] 价格范围内的所有细粒度区间
        3. 这样更准确地反映筹码的真实分布，而不是简单按收盘价分配
        
        示例实现思路：
        ------------
        # 伪代码示例
        for each_kline in df:
            price_range = [kline.low, kline.high]  # K线的价格区间
            volume = kline.volume
            
            # 找到覆盖这个价格区间的所有细粒度区间
            covered_bins = get_bins_in_range(price_range, price_step)
            
            # 将成交量均匀分配到这些区间（或按其他分布）
            volume_per_bin = volume / len(covered_bins)
            for bin in covered_bins:
                chip_distribution[bin] += volume_per_bin
        
        优势：
        - 更准确：考虑了K线的价格波动范围，而不是单一价格点
        - 更真实：反映了成交可能发生在 [low, high] 任何位置的事实
        - 更平滑：避免了按收盘价分配导致的分布突变
        
        注意：
        - 燃料 = 筹码峰 = 本方法返回的 ChipPeak 对象
        - chip_amounts 就是"燃料" - 每个价格区间的筹码量
        - 筹码峰是状态参数，需要根据上一个筹码峰进行动态演变
        - 如果 previous_chip_peak 为 None，表示首次计算，需要初始化
        - 此方法通常在 ThermalParamsCalculator.calculate() 内部调用
        - df 传入所有历史数据，计算函数内部按需使用
        """
        pass
