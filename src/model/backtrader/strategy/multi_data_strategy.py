"""
多数据源策略示例
演示如何使用日线、分时、周线等多种数据源
"""
import backtrader as bt
from model.backtrader.strategy.base import BaseStrategy
import pandas as pd


class MultiDataStrategy(BaseStrategy):
    """
    多数据源策略示例
    
    策略逻辑：
    - 使用分时数据（60分钟）进行触发判断
    - 使用日线数据计算长期指标（如周线、月线）
    - 使用周线数据判断大趋势
    """
    
    params = (
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        
        # 主数据源（分时数据，用于触发判断）
        # self.data 就是主数据源（第一个添加的数据源）
        
        # 获取其他数据源
        try:
            self.daily_data = self.get_data("000651_d")  # 日线数据
        except ValueError:
            self.daily_data = None
        
        try:
            self.weekly_data = self.get_data("000651_w")  # 周线数据
        except ValueError:
            self.weekly_data = None
        
        # 在主数据源（分时）上计算短期指标
        if len(self.data.close) > 20:
            self.sma_short = bt.indicators.SMA(self.data.close, period=20)
        
        # 在日线数据上计算长期指标
        if self.daily_data and len(self.daily_data.close) > 60:
            self.sma_long_daily = bt.indicators.SMA(self.daily_data.close, period=60)
    
    def next(self):
        """
        策略主逻辑
        
        注意：next() 是基于主数据源（分时数据）触发的
        每次分时数据更新时，这个方法会被调用
        """
        # 1. 获取主数据源（分时）的当前价格
        minute_price = self.get_current_price()  # 主数据源的价格
        
        # 2. 获取日线数据的最新价格（可能不是当前时刻，而是最新的日线收盘价）
        if self.daily_data:
            try:
                daily_price = self.daily_data.close[0]  # 最新的日线收盘价
                daily_df = self.get_dataframe("000651_d")  # 获取完整日线数据
                
                # 计算日线指标（例如：最近30天的平均价格）
                if len(daily_df) >= 30:
                    daily_avg_30 = daily_df['close'].tail(30).mean()
            except (IndexError, ValueError):
                daily_price = None
                daily_avg_30 = None
        else:
            daily_price = None
            daily_avg_30 = None
        
        # 3. 获取周线数据
        if self.weekly_data:
            try:
                weekly_price = self.weekly_data.close[0]  # 最新的周线收盘价
                weekly_df = self.get_dataframe("000651_w")  # 获取完整周线数据
            except (IndexError, ValueError):
                weekly_price = None
                weekly_df = None
        else:
            weekly_price = None
            weekly_df = None
        
        # 4. 基于分时数据判断（主数据源）
        # 这里可以根据分时数据的指标进行交易判断
        if self.order:
            return
        
        # 示例策略：结合分时和日线数据
        if self.daily_data and daily_avg_30:
            # 分时价格低于日线30日均价，且分时短期均线上穿
            if (minute_price < daily_avg_30 * 0.95 and 
                not self.position):
                # 买入
                size = self.calculate_position_size(cash_ratio=0.5)
                if size > 0:
                    self.log(f'分时价格低于日线30日均价，买入。分时: {minute_price:.2f}, 日线均价: {daily_avg_30:.2f}')
                    self.buy(size=size)
            
            # 分时价格高于日线30日均价，卖出
            elif (minute_price > daily_avg_30 * 1.05 and 
                  self.position):
                size = self.calculate_position_size(position_ratio=1.0)
                if size > 0:
                    self.log(f'分时价格高于日线30日均价，卖出。分时: {minute_price:.2f}, 日线均价: {daily_avg_30:.2f}')
                    self.sell(size=size)


class SimpleMultiDataStrategy(BaseStrategy):
    """
    简单的多数据源策略示例
    """
    
    def __init__(self):
        super().__init__()
        
        # 主数据源（分时，用于触发）
        # self.data 就是主数据源
        
        # 获取日线数据
        try:
            self.daily_data = self.get_data("000651_d")
        except ValueError:
            self.daily_data = None
    
    def next(self):
        """基于分时触发，使用日线数据判断"""
        if self.order:
            return
        
        # 获取分时价格（主数据源）
        minute_price = self.get_current_price()
        
        # 获取日线数据
        if self.daily_data:
            try:
                # 获取日线完整数据
                daily_df = self.get_dataframe("000651_d")
                
                if len(daily_df) >= 20:
                    # 计算日线20日均价
                    daily_ma20 = daily_df['close'].tail(20).mean()
                    
                    # 策略：分时价格低于日线20日均价时买入
                    if minute_price < daily_ma20 * 0.98 and not self.position:
                        self.buy_with_ratio(cash_ratio=0.5)
                    
                    # 分时价格高于日线20日均价时卖出
                    elif minute_price > daily_ma20 * 1.02 and self.position:
                        self.sell_with_ratio(position_ratio=1.0)
            except (IndexError, ValueError):
                pass
