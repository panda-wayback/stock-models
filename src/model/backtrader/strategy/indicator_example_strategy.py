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
        
        # 3. 存储指标（默认按日期存储，使用当前分时数据的日期）
        # 不需要指定 date，会自动使用当前数据的日期
        self.set_indicator('chip_peak', chip_peak)
        
        # 4. 计算并存储其他指标（也按日期存储）
        momentum = self.calculate_custom_indicator(full_df)
        self.set_indicator('momentum', momentum)
        
        # 5. 获取最新指标
        latest_chip_peak = self.get_indicator('chip_peak')
        
        # 6. 获取指定日期的指标
        current_date = self.data.datetime.date(0)
        today_chip_peak = self.get_indicator('chip_peak', date=current_date)
        
        # 7. 获取指标历史列表（按日期排序）
        chip_peak_history = self.get_indicator_history('chip_peak', as_list=True)
        # 返回: [(date1, value1), (date2, value2), ...]
        
        # 8. 遍历指标历史
        # for date, value in chip_peak_history:
        #     print(f"{date}: {value}")
        
        # 9. 使用指标进行交易决策
        if latest_chip_peak:
            avg_price = latest_chip_peak.get('avg_price', 0)
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
        
        # 10. 在策略结束时，可以查看所有指标
        if len(full_df) == len(self.data.close):  # 最后一天
            self.log(f'所有指标: {self.list_indicators()}', doprint=True)
            self.log(f'筹码峰历史记录数: {len(chip_peak_history)}', doprint=True)
            
            # 查看最近几天的指标
            if chip_peak_history:
                self.log('最近5天的筹码峰:', doprint=True)
                for date, value in chip_peak_history[-5:]:
                    self.log(f'  {date}: 均价={value.get("avg_price", 0):.2f}', doprint=True)


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
        
        # 存储指标（默认按日期存储，使用当前分时数据的日期）
        self.set_indicator('price', current_price)
        self.set_indicator('sma', sma_value)
        
        # 获取最新指标
        price = self.get_indicator('price')
        sma = self.get_indicator('sma')
        
        # 获取指标历史列表（按日期排序）
        price_history = self.get_indicator_history('price', as_list=True)
        # 返回: [(date1, price1), (date2, price2), ...]
        
        # 遍历价格历史
        # for date, price_value in price_history:
        #     print(f"{date}: {price_value:.2f}")
        
        # 使用指标
        if price and sma_value:
            if price > sma_value and not self.position:
                self.buy()
            elif price < sma_value and self.position:
                self.sell()
