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
        price_step: float = 0.01,
        num_segments: int = 100
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
        - price_step: 价格步长（固定为0.01元，即一分钱）
            固定值：0.01（一分钱）
        
        - num_segments: 价格分段数量（默认100，可调整）
            作用：将价格范围 [0, 最高价] 分成多少份
            默认值：100
            说明：
                - 可以根据需要调整为更多份（如200、500等）
                - 份数越多，价格区间越精细，但计算量也越大
                - 建议范围：100-500
            
            价格区间划分规则：
            ============================================
            1. 价格步长固定为 0.01元（一分钱）
            2. 根据当前最高价格，将价格范围 [0, 最高价] 分成 N 份
               - 默认 N = 100（可调整，建议100或更多）
               - 每份的宽度 = 最高价 / N
            3. 每份内部再按 0.01元 的步长细分
               - 例如：最高价=10元，分成100份，每份=0.1元
               - 每份内部有 0.1/0.01 = 10 个细粒度区间
               - 总区间数 = 100 * 10 = 1000 个区间
            
            示例：
            ------------
            假设当前最高价 = 5.0元，分成100份：
            - 每份宽度 = 5.0 / 100 = 0.05元
            - 每份内部细分数 = 0.05 / 0.01 = 5 个区间
            - 总区间数 = 100 * 5 = 500 个区间
            - 价格范围：[0.00, 0.01, 0.02, ..., 4.99, 5.00]
            
            假设当前最高价 = 10.0元，分成100份：
            - 每份宽度 = 10.0 / 100 = 0.1元
            - 每份内部细分数 = 0.1 / 0.01 = 10 个区间
            - 总区间数 = 100 * 10 = 1000 个区间
            
            假设当前最高价 = 50.0元，分成100份：
            - 每份宽度 = 50.0 / 100 = 0.5元
            - 每份内部细分数 = 0.5 / 0.01 = 50 个区间
            - 总区间数 = 100 * 50 = 5000 个区间
        
        返回:
        ChipPeak 对象（当前状态的筹码峰）
        
        计算方式（区间合并法）：
        ============================================
        推荐使用"价格步长 + 区间合并"的方式计算筹码峰：
        
        1. 使用 price_step=0.01 定义细粒度价格区间（一分钱一个区间）
        2. 根据当前最高价，确定价格范围 [0, 最高价]
        3. 将价格范围分成 num_segments 份（默认100份），每份内部按0.01元细分
        4. 对于每个K线，将其成交量按比例分配到 [low, high] 价格范围内的所有细粒度区间
        
        示例实现思路：
        ------------
        # 伪代码示例
        max_price = df['high'].max()  # 当前最高价
        segment_width = max_price / num_segments  # 每份宽度
        
        # 创建细粒度价格区间（基于0.01元步长）
        price_bins = create_price_bins(0, max_price, price_step=0.01)
        
        for each_kline in df:
            price_range = [kline.low, kline.high]  # K线的价格区间
            volume = kline.volume
            
            # 找到覆盖这个价格区间的所有细粒度区间
            covered_bins = get_bins_in_range(price_range, price_bins)
            
            # 将成交量均匀分配到这些区间（或按其他分布）
            volume_per_bin = volume / len(covered_bins)
            for bin in covered_bins:
                chip_distribution[bin] += volume_per_bin
        
        优势：
        - 固定步长0.01元，保证精度一致
        - 根据最高价动态调整区间数量，适应不同价格水平的股票
        - 区间合并法更准确地反映筹码的真实分布
        
        注意：
        - 燃料 = 筹码峰 = 本方法返回的 ChipPeak 对象
        - chip_amounts 就是"燃料" - 每个价格区间的筹码量
        - 筹码峰是状态参数，需要根据上一个筹码峰进行动态演变
        - 如果 previous_chip_peak 为 None，表示首次计算，需要初始化
        - 此方法通常在 ThermalParamsCalculator.calculate() 内部调用
        - df 传入所有历史数据，计算函数内部按需使用
        """
        pass
