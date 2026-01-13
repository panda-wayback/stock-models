"""
指标存储和使用示例策略
演示如何使用完整数据和指标存储功能
"""
import backtrader as bt
from model.backtrader.strategy.base import BaseStrategy
from typing import Dict, List
import pandas as pd


class IndicatorExampleStrategy(BaseStrategy):
    """
    指标存储示例策略
    
    演示：
    1. 获取完整历史数据
    2. 计算自定义指标（如筹码峰）
    3. 存储指标
    4. 获取历史指标
    """
    
    params = (
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        
        # 可以在这里初始化一些计算指标的工具
        pass
    
    def calculate_chip_peak(self, df: pd.DataFrame, lookback: int = 60) -> Dict:
        """
        计算筹码峰（示例）
        
        参数:
        - df: 历史数据 DataFrame
        - lookback: 回溯周期
        
        返回:
        筹码峰数据字典
        """
        # 这里只是示例，实际计算需要根据你的筹码峰算法
        recent_df = df.tail(lookback)
        
        # 示例：计算价格分布
        price_range = recent_df['high'].max() - recent_df['low'].min()
        avg_price = recent_df['close'].mean()
        total_volume = recent_df['volume'].sum()
        
        return {
            'price_range': price_range,
            'avg_price': avg_price,
            'total_volume': total_volume,
            'price_levels': {
                'high': recent_df['high'].max(),
                'low': recent_df['low'].min(),
                'close': recent_df['close'].iloc[-1],
            }
        }
    
    def calculate_custom_indicator(self, df: pd.DataFrame) -> float:
        """
        计算自定义指标（示例）
        
        参数:
        - df: 历史数据 DataFrame
        
        返回:
        指标值
        """
        # 示例：计算价格动量
        if len(df) < 10:
            return 0.0
        
        recent_prices = df['close'].tail(10)
        momentum = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
        return momentum
    
    def next(self):
        """策略主逻辑"""
        # 1. 获取完整历史数据
        full_df = self.get_full_dataframe()
        
        if len(full_df) < 60:
            return  # 数据不足，跳过
        
        # 2. 计算指标（例如：筹码峰）
        chip_peak = self.calculate_chip_peak(full_df, lookback=60)
        
        # 3. 存储当前指标（不按日期）
        self.set_indicator('chip_peak', chip_peak)
        
        # 4. 存储历史指标（按日期）
        current_date = self.data.datetime.date(0)
        self.set_indicator('chip_peak_history', chip_peak, date=current_date)
        
        # 5. 计算并存储其他指标
        momentum = self.calculate_custom_indicator(full_df)
        self.set_indicator('momentum', momentum, date=current_date)
        
        # 6. 获取之前存储的指标
        previous_chip_peak = self.get_indicator('chip_peak')
        historical_chip_peak = self.get_indicator('chip_peak_history', date=current_date)
        
        # 7. 获取指标历史
        chip_peak_history = self.get_indicator_history('chip_peak_history')
        
        # 8. 使用指标进行交易决策
        if previous_chip_peak:
            avg_price = previous_chip_peak.get('avg_price', 0)
            current_price = self.get_current_price()
            
            # 示例策略：价格低于平均筹码价格时买入
            if not self.position and current_price < avg_price * 0.95:
                if self.order is None:
                    self.log(f'价格低于筹码峰均价，买入。当前价格: {current_price:.2f}, 均价: {avg_price:.2f}')
                    self.buy()
            
            # 价格高于平均筹码价格时卖出
            elif self.position and current_price > avg_price * 1.05:
                if self.order is None:
                    self.log(f'价格高于筹码峰均价，卖出。当前价格: {current_price:.2f}, 均价: {avg_price:.2f}')
                    self.sell()
        
        # 9. 在策略结束时，可以查看所有指标
        if len(full_df) == len(self.data.close):  # 最后一天
            self.log(f'所有指标: {self.list_indicators()}', doprint=True)
            self.log(f'筹码峰历史记录数: {len(chip_peak_history)}', doprint=True)


class SimpleIndicatorStrategy(BaseStrategy):
    """
    简单指标存储示例
    
    演示基本的指标存储和使用
    """
    
    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SMA(self.data.close, period=20)
    
    def next(self):
        """策略主逻辑"""
        # 获取完整数据
        df = self.get_all_data()
        
        # 计算并存储简单指标
        current_price = self.get_current_price()
        sma_value = self.sma[0]
        
        # 存储当前指标
        self.set_indicator('price', current_price)
        self.set_indicator('sma', sma_value)
        
        # 存储历史指标
        current_date = self.data.datetime.date(0)
        self.set_indicator('price_history', current_price, date=current_date)
        self.set_indicator('sma_history', sma_value, date=current_date)
        
        # 获取指标
        price = self.get_indicator('price')
        price_history = self.get_indicator_history('price_history')
        
        # 使用指标
        if price and sma_value:
            if price > sma_value and not self.position:
                self.buy()
            elif price < sma_value and self.position:
                self.sell()
