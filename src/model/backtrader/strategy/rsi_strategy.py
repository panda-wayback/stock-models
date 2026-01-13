"""
RSI 策略示例
基于日线数据计算多个周期的RSI
"""
import backtrader as bt
from model.backtrader.strategy.base import BaseStrategy
from model.backtrader.trigger.signal_trigger import ThresholdSignal
from typing import Dict
import pandas as pd
import numpy as np


class RSIStrategy(BaseStrategy):
    """
    RSI 策略（多周期）
    
    策略逻辑：
    - 基于日线数据计算多个周期的RSI（3天、5天、周、半月、月）
    - 在分时数据触发时，使用日线RSI进行判断
    - RSI < 超卖阈值 → 买入
    - RSI > 超买阈值 → 卖出
    """
    
    params = (
        ('rsi_low', 30),        # RSI 超卖阈值
        ('rsi_high', 70),       # RSI 超买阈值
        ('buy_ratio', 1.0),     # 买入时使用的现金比例（0.0-1.0）
        ('sell_ratio', 1.0),    # 卖出时使用的持仓比例（0.0-1.0）
        ('stop_loss', 0.05),    # 止损比例（5%）
        ('take_profit', 0.15),  # 止盈比例（15%）
        ('rsi_sell_threshold', 60),  # RSI卖出阈值（降低到60，更及时止盈）
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        
        # 自动获取日线数据（用于计算RSI）
        # 从数据源名称中提取股票代码
        self.symbol = None
        self.daily_data_name = None
        
        for data_name in self.list_data_sources():
            if '_d' in data_name:
                self.symbol = data_name.replace('_d', '')
                self.daily_data_name = data_name
                break
        
        if self.daily_data_name:
            try:
                self.daily_data = self.get_data(self.daily_data_name)
            except ValueError:
                self.daily_data = None
        else:
            self.daily_data = None
        
        if self.daily_data is None:
            # 如果没有日线数据，使用主数据源（不推荐）
            self.daily_data = self.data
            if self.params.printlog:
                self.log("警告：未找到日线数据，使用主数据源计算RSI", doprint=True)
        
        # RSI 周期配置（基于日线数据）
        # 3天、5天、周(7天)、半月(15天)、月(30天)
        self.rsi_periods = {
            'rsi_3d': 3,           # 3天
            'rsi_5d': 5,           # 5天
            'rsi_week': 7,         # 周（7天）
            'rsi_halfmonth': 15,   # 半月（15天）
            'rsi_month': 30        # 月（30天）
        }
    
    def calculate_rsi(self, prices: pd.Series, period: int) -> float:
        """
        计算RSI（相对强弱指标）- 使用最佳实践方法
        
        RSI计算公式（Wilder's Smoothing Method）：
        1. 计算价格变化 delta = price[t] - price[t-1]
        2. 分离上涨和下跌：gain = max(delta, 0), loss = max(-delta, 0)
        3. 计算平均收益和平均损失（使用Wilder平滑，即EMA）
        4. RS = 平均收益 / 平均损失
        5. RSI = 100 - (100 / (1 + RS))
        
        参数:
        - prices: 价格序列（pandas Series）
        - period: RSI周期（天数）
        
        返回:
        RSI值（0-100），数据不足时返回50.0（中性值）
        """
        if len(prices) < period + 1:
            return 50.0  # 数据不足，返回中性值
        
        # 计算价格变化
        delta = prices.diff()
        
        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        # 使用Wilder平滑方法（指数移动平均，alpha = 1/period）
        # 这是RSI的标准计算方法
        avg_gain = gain.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()
        
        # 避免除零
        avg_loss = avg_loss.replace(0, np.nan)
        
        # 计算RS（相对强度）
        rs = avg_gain / avg_loss
        
        # 计算RSI
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        # 获取最后一个值
        rsi_value = rsi.iloc[-1]
        
        # 处理异常值
        if pd.isna(rsi_value) or np.isinf(rsi_value):
            return 50.0
        
        # 确保RSI在0-100范围内
        return max(0.0, min(100.0, rsi_value))
    
    def calculate_all_rsi(self) -> Dict[str, float]:
        """
        计算所有周期的RSI（基于日线数据）
        
        返回:
        字典 {周期名: RSI值}
        """
        if not self.daily_data_name:
            if self.params.printlog and len(self.data.close) % 500 == 0:
                self.log(f"未找到日线数据源，可用数据源: {self.list_data_sources()}", doprint=True)
            return {}
        
        # 获取日线完整数据
        try:
            daily_df = self.get_dataframe(self.daily_data_name)
        except (ValueError, KeyError) as e:
            if self.params.printlog and len(self.data.close) % 500 == 0:
                self.log(f"获取日线数据失败: {e}, 数据源={self.daily_data_name}", doprint=True)
            return {}
        
        if len(daily_df) < 30:  # 至少需要30天数据（最长周期是30天）
            if self.params.printlog and len(self.data.close) % 500 == 0:
                self.log(f"日线数据不足: {len(daily_df)} 天，需要至少30天", doprint=True)
            return {}
        
        prices = daily_df['close']
        rsi_values = {}
        
        # 计算每个周期的RSI
        for name, period in self.rsi_periods.items():
            if len(prices) >= period + 1:
                rsi_value = self.calculate_rsi(prices, period)
                rsi_values[name] = rsi_value
            else:
                rsi_values[name] = 50.0  # 数据不足，返回中性值
        
        return rsi_values
    
    def next(self):
        """策略主逻辑（基于分时数据触发，使用日线RSI判断）"""
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 1. 计算所有周期的RSI（基于日线数据）
        rsi_values = self.calculate_all_rsi()
        
        if not rsi_values:
            # 添加调试信息
            if self.params.printlog and len(self.data.close) % 100 == 0:  # 每100个bar打印一次
                self.log(f"RSI计算失败：数据源={self.daily_data_name}, 数据源列表={self.list_data_sources()}", doprint=True)
            return  # 数据不足，跳过
        
        # 2. 存储RSI指标（按日期）
        for name, value in rsi_values.items():
            self.set_indicator(name, value)
        
        # 获取所有RSI值
        rsi_3d = rsi_values.get('rsi_3d', 50.0)
        rsi_5d = rsi_values.get('rsi_5d', 50.0)
        rsi_week = rsi_values.get('rsi_week', 50.0)
        rsi_halfmonth = rsi_values.get('rsi_halfmonth', 50.0)
        rsi_month = rsi_values.get('rsi_month', 50.0)
        
        # 定期打印RSI值（用于调试）
        if self.params.printlog and len(self.data.close) % 200 == 0:
            self.log(
                f'RSI值 - 3日: {rsi_3d:.1f}, 5日: {rsi_5d:.1f}, 周: {rsi_week:.1f}, '
                f'半月: {rsi_halfmonth:.1f}, 月: {rsi_month:.1f}',
                doprint=True
            )
        
        # 3. 策略逻辑：使用多个RSI周期综合判断
        # 优先处理持仓情况（止损、止盈、RSI卖出）
        
        if self.position:
            # 计算当前盈亏
            current_price = self.get_current_price()
            cost_basis = self.position.price  # 持仓成本价
            if cost_basis > 0:
                profit_pct = (current_price - cost_basis) / cost_basis
                
                # 止损：亏损超过阈值
                if profit_pct <= -self.params.stop_loss:
                    size = self.calculate_position_size(position_ratio=self.params.sell_ratio)
                    if size > 0:
                        self.log(
                            f'止损卖出 {size} 股，亏损 {profit_pct*100:.2f}%。'
                            f'成本: {cost_basis:.2f}, 当前: {current_price:.2f}。'
                            f'RSI: 3日={rsi_3d:.1f}, 5日={rsi_5d:.1f}, 周={rsi_week:.1f}, 月={rsi_month:.1f}'
                        )
                        self.sell(size=size)
                        return
                
                # 止盈：盈利超过阈值
                if profit_pct >= self.params.take_profit:
                    size = self.calculate_position_size(position_ratio=self.params.sell_ratio)
                    if size > 0:
                        self.log(
                            f'止盈卖出 {size} 股，盈利 {profit_pct*100:.2f}%。'
                            f'成本: {cost_basis:.2f}, 当前: {current_price:.2f}。'
                            f'RSI: 3日={rsi_3d:.1f}, 5日={rsi_5d:.1f}, 周={rsi_week:.1f}, 月={rsi_month:.1f}'
                        )
                        self.sell(size=size)
                        return
                
                # RSI卖出条件1：周RSI或月RSI超过超买阈值（强信号）
                if rsi_week > self.params.rsi_high or rsi_month > self.params.rsi_high:
                    size = self.calculate_position_size(position_ratio=self.params.sell_ratio)
                    if size > 0:
                        self.log(
                            f'RSI 超买信号，卖出 {size} 股。'
                            f'3日: {rsi_3d:.1f}, 5日: {rsi_5d:.1f}, 周: {rsi_week:.1f}, '
                            f'半月: {rsi_halfmonth:.1f}, 月: {rsi_month:.1f}'
                        )
                        self.sell(size=size)
                        return
                
                # RSI卖出条件2：周RSI超过卖出阈值，且盈利为正（及时止盈）
                if rsi_week > self.params.rsi_sell_threshold and profit_pct > 0.02:  # 至少盈利2%
                    size = self.calculate_position_size(position_ratio=self.params.sell_ratio)
                    if size > 0:
                        self.log(
                            f'RSI 卖出信号（及时止盈），卖出 {size} 股，盈利 {profit_pct*100:.2f}%。'
                            f'3日: {rsi_3d:.1f}, 5日: {rsi_5d:.1f}, 周: {rsi_week:.1f}, 月: {rsi_month:.1f}'
                        )
                        self.sell(size=size)
                        return
                
                # RSI卖出条件3：多个短期RSI都较高，且月RSI也在上升（趋势反转）
                if (rsi_3d > 60 and rsi_5d > 55 and rsi_week > 50 and 
                    rsi_month > rsi_halfmonth):  # 月RSI在上升
                    size = self.calculate_position_size(position_ratio=self.params.sell_ratio)
                    if size > 0:
                        self.log(
                            f'RSI 趋势反转信号，卖出 {size} 股。'
                            f'3日: {rsi_3d:.1f}, 5日: {rsi_5d:.1f}, 周: {rsi_week:.1f}, '
                            f'半月: {rsi_halfmonth:.1f}, 月: {rsi_month:.1f}'
                        )
                        self.sell(size=size)
                        return
        
        # 买入逻辑：需要更严格的确认条件
        if not self.position:
            # 获取RSI历史，判断趋势
            rsi_week_history = self.get_indicator_history('rsi_week', as_list=True)
            rsi_month_history = self.get_indicator_history('rsi_month', as_list=True)
            
            # 判断RSI是否在上升趋势（避免在下跌趋势中买入）
            rsi_week_rising = False
            rsi_month_rising = False
            if len(rsi_week_history) >= 2:
                rsi_week_rising = rsi_week_history[-1][1] > rsi_week_history[-2][1]
            if len(rsi_month_history) >= 2:
                rsi_month_rising = rsi_month_history[-1][1] > rsi_month_history[-2][1]
            
            # 买入条件1：周RSI和月RSI都低于超卖阈值，且月RSI在上升（强信号）
            buy_condition_1 = (rsi_week < self.params.rsi_low and 
                              rsi_month < self.params.rsi_low and
                              rsi_month_rising)  # 月RSI在上升，说明可能见底
            
            # 买入条件2：月RSI低于超卖阈值，周RSI也在低位，且5日RSI极低（超卖反弹）
            buy_condition_2 = (rsi_month < self.params.rsi_low and 
                              rsi_week < self.params.rsi_low * 1.1 and  # 周RSI也在低位
                              rsi_5d < self.params.rsi_low * 0.8)  # 5日RSI极低（超卖）
            
            # 买入条件3：周RSI低于超卖阈值，且多个短期RSI都在极低位（超卖反弹）
            buy_condition_3 = (rsi_week < self.params.rsi_low and 
                              rsi_3d < self.params.rsi_low * 0.7 and  # 3日RSI极低
                              rsi_5d < self.params.rsi_low * 0.8 and  # 5日RSI极低
                              rsi_week_rising)  # 周RSI在上升
            
            if buy_condition_1 or buy_condition_2 or buy_condition_3:
                size = self.calculate_position_size(cash_ratio=self.params.buy_ratio)
                if size > 0:
                    condition_type = "强" if buy_condition_1 else ("中" if buy_condition_2 else "短")
                    trend_info = f"月RSI{'↑' if rsi_month_rising else '↓'}, 周RSI{'↑' if rsi_week_rising else '↓'}"
                    self.log(
                        f'RSI 超卖信号({condition_type})，买入 {size} 股。{trend_info}。'
                        f'3日: {rsi_3d:.1f}, 5日: {rsi_5d:.1f}, 周: {rsi_week:.1f}, '
                        f'半月: {rsi_halfmonth:.1f}, 月: {rsi_month:.1f}'
                    )
                    self.buy(size=size)
