import backtrader as bt
import os
import sys

# 确保 src 目录在路径中
sys.path.append(os.path.join(os.getcwd(), 'src'))

from utils.stock_data.bt_adapter import load_data_to_bt

class FlexibleStrategy(bt.Strategy):
    """
    一个展示 Backtrader 灵活性的示例策略
    包含逻辑：
    1. 动态止损：买入后，止损位随价格上涨而上移（移动止损）
    2. 状态机逻辑：只有在发生特定价格穿透后，才进入“观察期”
    3. 复杂的仓位管理：分批建仓
    """
    params = (
        ('maperiod', 15),
        ('printlog', True),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')

    def __init__(self):
        # 基础指标
        self.dataclose = self.datas[0].close
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod)
        
        # 策略状态变量
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.stop_price = None  # 动态止损位
        self.state = 'IDLE'     # 状态：IDLE (空闲), WATCHING (观察), POSITION (持仓)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入已执行, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'卖出已执行, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
            
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/金额不足/拒绝')

        self.order = None

    def next(self):
        """核心策略逻辑 - 这里展示了 event-driven 的自由度"""
        
        # 如果有订单在处理中，不做任何事
        if self.order:
            return

        # 状态机逻辑
        if self.state == 'IDLE':
            # 如果价格上穿均线，进入观察状态
            if self.dataclose[0] > self.sma[0] and self.dataclose[-1] <= self.sma[-1]:
                self.state = 'WATCHING'
                self.log('进入【观察】状态：价格上穿均线')

        elif self.state == 'WATCHING':
            # 在观察状态下，如果价格继续走强（比如创3日新高），则买入
            if self.dataclose[0] > max(self.dataclose.get(ago=-1, size=3)):
                self.log('执行买入：满足观察期后的突破条件')
                self.order = self.buy()
                self.state = 'POSITION'
                self.stop_price = self.dataclose[0] * 0.95 # 初始止损 5%

        elif self.state == 'POSITION':
            # 持仓状态下的复杂逻辑：移动止损
            # 如果价格上涨，止损位也跟着上涨，但止损位从不下跌
            current_stop = self.dataclose[0] * 0.95
            if current_stop > self.stop_price:
                self.stop_price = current_stop
                # self.log(f'更新移动止损位至: {self.stop_price:.2f}')

            # 检查是否触发止损
            if self.dataclose[0] < self.stop_price:
                self.log(f'触发移动止损卖出，触发价: {self.dataclose[0]:.2f}, 止损价: {self.stop_price:.2f}')
                self.order = self.sell()
                self.state = 'IDLE'
            
            # 或者均线死叉卖出（另一种退出逻辑）
            elif self.dataclose[0] < self.sma[0]:
                self.log('均线死叉卖出')
                self.order = self.sell()
                self.state = 'IDLE'

if __name__ == '__main__':
    # 初始化引擎
    cerebro = bt.Cerebro()

    # 加载数据
    data = load_data_to_bt(
        symbol="000651", 
        start_date="2020-01-01", 
        end_date="2023-12-31", 
        frequency="d"
    )
    
    if data is not None:
        cerebro.adddata(data)
        cerebro.addstrategy(FlexibleStrategy)
        
        # 设置初始资金
        cerebro.broker.setcash(100000.0)
        # 设置佣金 (0.1%)
        cerebro.broker.setcommission(commission=0.001)

        print('期初资金: %.2f' % cerebro.broker.getvalue())
        cerebro.run()
        print('期末资金: %.2f' % cerebro.broker.getvalue())
        
        # 绘图 (需要安装 matplotlib)
        # cerebro.plot()
    else:
        print("未获取到数据，请检查网络或 BaoStock 状态")
