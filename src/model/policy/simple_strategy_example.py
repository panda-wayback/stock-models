"""
最简单的 Backtrader 策略示例
使用格力股票数据，实现简单的移动平均线买入卖出策略
支持 T+1 限制（A股当天买入不能当天卖出）
"""
import backtrader as bt
import pandas as pd
from model.bt_adapter import load_data_to_bt


class SimpleMAStrategy(bt.Strategy):
    """
    优化的移动平均线策略
    改进点：
    1. 使用全部可用资金买入
    2. 增加止损止盈机制
    3. 增加趋势过滤（长期均线）
    4. 增加成交量确认
    5. 最小持仓周期，避免频繁交易
    """
    params = (
        ('ma_short', 5),    # 短期均线周期
        ('ma_long', 20),   # 长期均线周期
        ('ma_trend', 30),   # 趋势均线周期（用于过滤，降低到30）
        ('stop_loss', 0.05), # 止损比例 5%
        ('take_profit', 0.20), # 止盈比例 20%（提高止盈）
        ('min_hold_days', 3), # 最小持仓天数（降低到3天）
        ('volume_factor', 1.0), # 成交量放大倍数（降低要求，只要不低于均量即可）
        ('debug', False),   # 是否打印调试信息
        ('t_plus_one', True), # 是否启用 T+1 限制（A股当天买入不能当天卖出）
    )

    def __init__(self):
        # 计算移动平均线
        self.ma_short = bt.indicators.SMA(self.data.close, period=self.params.ma_short)
        self.ma_long = bt.indicators.SMA(self.data.close, period=self.params.ma_long)
        self.ma_trend = bt.indicators.SMA(self.data.close, period=self.params.ma_trend)
        
        # 计算成交量均线
        self.volume_ma = bt.indicators.SMA(self.data.volume, period=20)
        
        # 记录交叉信号
        self.crossover = bt.indicators.CrossOver(self.ma_short, self.ma_long)
        
        # 记录订单和买入价格
        self.order = None
        self.buy_price = None
        self.buy_date = None
        self.buy_datetime = None  # 买入的完整时间（用于分钟线数据）
        self.stop_loss_price = None
        self.take_profit_price = None

    def _get_trading_date(self, dt):
        """
        从时间中提取交易日（日期部分）
        支持 datetime 和 date 类型
        """
        if dt is None:
            return None
        if isinstance(dt, pd.Timestamp):
            return dt.date()
        if hasattr(dt, 'date'):
            return dt.date()
        if isinstance(dt, type(pd.Timestamp.now().date())):
            return dt
        # 尝试转换为日期
        try:
            return pd.to_datetime(dt).date()
        except:
            return None

    def _can_sell_today(self):
        """
        检查是否可以卖出（T+1 限制）
        返回 True 表示可以卖出，False 表示不能卖出（当天买入的不能当天卖）
        """
        if not self.params.t_plus_one:
            return True  # 不启用 T+1 限制
        
        if self.buy_datetime is None:
            return True  # 没有买入记录，理论上不应该到这里
        
        # 获取当前时间和买入时间的交易日
        current_dt = self.data.datetime.datetime(0) if hasattr(self.data.datetime, 'datetime') else self.data.datetime.date(0)
        buy_date = self._get_trading_date(self.buy_datetime)
        current_date = self._get_trading_date(current_dt)
        
        if buy_date is None or current_date is None:
            return True  # 无法判断，允许卖出
        
        # 判断是否在同一天：不是同一天才能卖出
        return buy_date != current_date

    def next(self):
        # 如果已有订单，不执行新操作
        if self.order:
            return

        # 如果已持仓，检查止损止盈
        if self.position:
            # 确保止损止盈价格已设置
            if self.stop_loss_price is None or self.take_profit_price is None:
                return
            
            # T+1 限制检查：当天买入的不能当天卖出
            if not self._can_sell_today():
                if self.params.debug:
                    print(f'T+1限制: 当天买入不能卖出, 买入时间={self.buy_datetime}, 当前时间={self.data.datetime.datetime(0) if hasattr(self.data.datetime, "datetime") else self.data.datetime.date(0)}')
                return  # 不能卖出，直接返回
            
            # 检查止损
            if self.data.close[0] <= self.stop_loss_price:
                self.order = self.close()  # 平仓所有持仓
                print(f'止损卖出: 日期={self.data.datetime.date(0)}, 价格={self.data.close[0]:.2f}, 买入价={self.buy_price:.2f}, 亏损={((self.data.close[0]/self.buy_price-1)*100):.2f}%')
                return
            
            # 检查止盈
            if self.data.close[0] >= self.take_profit_price:
                self.order = self.close()  # 平仓所有持仓
                print(f'止盈卖出: 日期={self.data.datetime.date(0)}, 价格={self.data.close[0]:.2f}, 买入价={self.buy_price:.2f}, 盈利={((self.data.close[0]/self.buy_price-1)*100):.2f}%')
                return
            
            # 检查死叉卖出（但需要满足最小持仓天数）
            if self.crossover < 0:
                days_held = (self.data.datetime.date(0) - self.buy_date).days if self.buy_date else 0
                if days_held >= self.params.min_hold_days:
                    self.order = self.close()  # 平仓所有持仓
                    profit_pct = ((self.data.close[0]/self.buy_price-1)*100) if self.buy_price else 0
                    print(f'死叉卖出: 日期={self.data.datetime.date(0)}, 价格={self.data.close[0]:.2f}, 买入价={self.buy_price:.2f}, 盈利={profit_pct:.2f}%')
                return
        
        # 如果没有持仓，检查买入信号
        else:
            # 买入条件：
            # 1. 短期均线上穿长期均线（金叉）
            # 2. 价格在趋势均线之上（确保是上升趋势）- 可选，如果数据不足则忽略
            # 3. 成交量不低于均量（确认突破）
            
            # 检查是否有足够数据计算趋势均线
            has_trend_data = len(self.data) > self.params.ma_trend
            
            # 买入条件（放宽）
            condition1 = self.crossover > 0  # 金叉
            condition2 = (not has_trend_data) or (self.data.close[0] > self.ma_trend[0])  # 趋势过滤（如果数据不足则忽略）
            condition3 = self.data.volume[0] >= self.volume_ma[0] * self.params.volume_factor  # 成交量确认
            
            if self.params.debug and self.crossover > 0:
                print(f'调试: 日期={self.data.datetime.date(0)}, 金叉={condition1}, 趋势={condition2} (价格={self.data.close[0]:.2f}, 趋势均线={self.ma_trend[0]:.2f if has_trend_data else "N/A"}), 成交量={condition3} (当前={self.data.volume[0]:.0f}, 均量={self.volume_ma[0]:.0f})')
            
            if condition1 and condition2 and condition3:
                # 计算买入数量：使用全部可用资金（考虑手续费，预留1%缓冲）
                cash = self.broker.getcash()
                price = self.data.close[0]
                # 预留1%作为手续费和滑点缓冲
                available_cash = cash * 0.99
                size = int(available_cash / price)
                
                if size > 0:
                    self.order = self.buy(size=size)
                    print(f'买入信号: 日期={self.data.datetime.date(0)}, 价格={price:.2f}, 数量={size}, 可用资金={cash:.2f}')

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                self.buy_date = self.data.datetime.date(0)
                # 记录买入的完整时间（用于 T+1 判断）
                if hasattr(self.data.datetime, 'datetime'):
                    self.buy_datetime = self.data.datetime.datetime(0)
                else:
                    self.buy_datetime = self.data.datetime.date(0)
                # 设置止损止盈价格
                self.stop_loss_price = self.buy_price * (1 - self.params.stop_loss)
                self.take_profit_price = self.buy_price * (1 + self.params.take_profit)
                print(f'买入执行: 价格={order.executed.price:.2f}, 数量={order.executed.size}, 成本={order.executed.value:.2f}')
                print(f'  止损价={self.stop_loss_price:.2f}, 止盈价={self.take_profit_price:.2f}')
            elif order.issell():
                # 计算盈利（使用实际执行的金额和成本）
                if self.buy_price:
                    cost = self.buy_price * abs(order.executed.size)
                    profit = order.executed.value - cost
                    profit_pct = ((order.executed.price/self.buy_price-1)*100)
                else:
                    profit = 0
                    profit_pct = 0
                print(f'卖出执行: 价格={order.executed.price:.2f}, 数量={abs(order.executed.size)}, 金额={order.executed.value:.2f}, 盈利={profit:.2f} ({profit_pct:.2f}%)')
                # 重置买入信息
                self.buy_price = None
                self.buy_date = None
                self.buy_datetime = None
                self.stop_loss_price = None
                self.take_profit_price = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if order.isbuy():
                print(f'买入订单被取消/保证金不足/被拒绝: 日期={self.data.datetime.date(0)}, 价格={self.data.close[0]:.2f}, 可用资金={self.broker.getcash():.2f}')
            else:
                print(f'卖出订单被取消/被拒绝: 日期={self.data.datetime.date(0)}')

        # 重置订单状态
        self.order = None

    def stop(self):
        """策略结束时的回调"""
        print(f'\n策略结束')
        final_value = self.broker.getvalue()
        initial_value = self.broker.startingcash
        total_return = ((final_value / initial_value) - 1) * 100
        print(f'初始资金: {initial_value:.2f}')
        print(f'最终资产价值: {final_value:.2f}')
        print(f'总收益率: {total_return:.2f}%')
        print(f'最终持仓: {self.position.size}')
        if self.position and self.buy_price:
            current_price = self.data.close[0]
            unrealized_profit = (current_price - self.buy_price) * self.position.size
            unrealized_pct = ((current_price / self.buy_price) - 1) * 100
            print(f'持仓成本: {self.buy_price:.2f}, 当前价: {current_price:.2f}, 浮动盈亏: {unrealized_profit:.2f} ({unrealized_pct:.2f}%)')


def run_backtest():
    """运行回测"""
    # 创建 Cerebro 引擎
    cerebro = bt.Cerebro()
    
    # 加载格力股票数据（000651）
    print("正在加载格力股票数据...")
    data = load_data_to_bt(
        symbol='000651',  # 格力股票代码
        start_date='2025-01-01',
        end_date='2025-12-31',
        frequency='5'
    )
    
    if data is None:
        print("无法加载数据，请检查数据源")
        return
    
    # 添加数据到引擎
    cerebro.adddata(data)
    
    # 添加策略（使用优化后的参数）
    cerebro.addstrategy(
        SimpleMAStrategy, 
        ma_short=5,       # 短期均线（5日）
        ma_long=20,       # 长期均线（20日）
        ma_trend=30,      # 趋势均线（30日，降低要求）
        stop_loss=0.05,   # 5%止损
        take_profit=0.20, # 20%止盈（提高止盈目标）
        min_hold_days=3,  # 最小持仓3天（降低要求）
        volume_factor=1.0, # 成交量只需不低于均量即可
        debug=False,      # 关闭调试信息（需要时可设为True）
        t_plus_one=True   # 启用 T+1 限制（A股规则：当天买入不能当天卖出）
    )
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)  # 10万元
    
    # 设置手续费（A股通常为万分之2.5，买卖双向）
    cerebro.broker.setcommission(commission=0.00002)
    
    # 打印初始资金
    print(f'初始资金: {cerebro.broker.getvalue():.2f}')
    
    # 运行回测
    print("\n开始回测...")
    cerebro.run()
    
    # 打印最终资金
    print(f'\n最终资金: {cerebro.broker.getvalue():.2f}')
    
    # 可选：绘制图表（需要 matplotlib）
    # cerebro.plot()


if __name__ == '__main__':
    run_backtest()
