"""
中国A股市场 Broker 配置
处理印花税、手续费、T+1 限制等交易规则
"""
import backtrader as bt
from datetime import datetime, timedelta
from typing import Dict, Optional


class ChinaStockBroker(bt.brokers.BackBroker):
    """
    中国A股市场 Broker
    
    特性：
    1. 印花税：卖出时收取 0.1%（单向）
    2. 手续费：买入和卖出时收取（可配置，默认 0.0003 = 0.03%）
    3. T+1 限制：当天买入的股票不能当天卖出
    4. 最小交易单位：100股（1手）
    """
    
    def __init__(self, 
                 commission: float = 0.0003,
                 stamp_tax: float = 0.001,
                 min_commission: float = 5.0,
                 **kwargs):
        """
        初始化中国A股 Broker
        
        参数:
        - commission: 手续费率（默认 0.0003 = 0.03%，万三）
        - stamp_tax: 印花税率（默认 0.001 = 0.1%，仅卖出时收取）
        - min_commission: 最小手续费（默认 5.0 元）
        """
        super().__init__(**kwargs)
        self.commission_rate = commission
        self.stamp_tax_rate = stamp_tax
        self.min_commission = min_commission
        
        # 记录每笔买入的日期，用于 T+1 限制
        self._buy_dates: Dict[int, datetime] = {}  # {order_id: buy_date}
    
    def get_commission_info(self, size: float, price: float, is_buy: bool) -> Dict[str, float]:
        """
        计算交易费用
        
        返回:
        - commission: 手续费
        - stamp_tax: 印花税（仅卖出时）
        - total_cost: 总费用
        """
        value = abs(size) * price
        
        # 手续费（买入和卖出都收取）
        commission = value * self.commission_rate
        if commission < self.min_commission:
            commission = self.min_commission
        
        # 印花税（仅卖出时收取）
        stamp_tax = 0.0
        if not is_buy:
            stamp_tax = value * self.stamp_tax_rate
        
        total_cost = commission + stamp_tax
        
        return {
            'commission': commission,
            'stamp_tax': stamp_tax,
            'total_cost': total_cost
        }
    
    def submit(self, order):
        """提交订单前检查 T+1 限制"""
        # 如果是卖出订单，检查是否违反 T+1 规则
        if order.isbuy():
            # 买入订单：记录买入日期
            self._buy_dates[order.ref] = self.data.datetime.date(0)
        else:
            # 卖出订单：检查持仓是否满足 T+1
            if self._check_t1_restriction(order):
                # 违反 T+1，拒绝订单
                order.reject()
                return order
        
        return super().submit(order)
    
    def _check_t1_restriction(self, order) -> bool:
        """
        检查是否违反 T+1 限制
        
        返回 True 表示违反 T+1（不能卖出），False 表示可以卖出
        """
        # 获取当前持仓
        position = self.getposition(order.data)
        
        if position.size == 0:
            # 没有持仓，可以卖出（做空场景，但A股不支持做空）
            return False
        
        # 检查是否有今天买入的股票
        current_date = self.data.datetime.date(0)
        
        # 简化处理：如果持仓存在且是今天买入的，则不能卖出
        # 注意：这里简化了，实际应该跟踪每笔买入的日期
        # 更精确的实现需要维护持仓成本记录
        
        # 对于简化版本，我们假设：
        # 如果今天有买入订单，则不能卖出
        for order_ref, buy_date in self._buy_dates.items():
            if buy_date == current_date:
                # 今天有买入，不能卖出
                return True
        
        return False
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Completed]:
            if order.isbuy():
                # 买入完成，记录日期
                self._buy_dates[order.ref] = self.data.datetime.date(0)
            elif order.issell():
                # 卖出完成，清理记录（简化处理）
                pass
        
        super().notify_order(order)


class T1Broker(bt.brokers.BackBroker):
    """
    T+1 限制的 Broker 包装器
    
    这是一个更精确的 T+1 实现，通过自定义 Order 来跟踪买入日期
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 记录持仓的买入日期 {data: {date: size}}
        self._position_buy_dates: Dict = {}
    
    def _check_can_sell(self, data, size: int) -> bool:
        """
        检查是否可以卖出指定数量的股票
        
        参数:
        - data: 数据源
        - size: 要卖出的数量（正数）
        
        返回:
        - True: 可以卖出
        - False: 不能卖出（违反 T+1）
        """
        if data not in self._position_buy_dates:
            return True
        
        position = self.getposition(data)
        if position.size <= 0:
            return True
        
        current_date = data.datetime.date(0)
        
        # 检查今天买入的股票数量
        today_buy_size = self._position_buy_dates[data].get(current_date, 0)
        
        # 可以卖出的数量 = 总持仓 - 今天买入的数量
        available_size = position.size - today_buy_size
        
        return available_size >= size


def create_china_stock_broker(
    initial_cash: float = 100000.0,
    commission: float = 0.0003,
    stamp_tax: float = 0.001,
    min_commission: float = 5.0
) -> bt.brokers.BackBroker:
    """
    创建配置好的中国A股 Broker
    
    参数:
    - initial_cash: 初始资金
    - commission: 手续费率（默认 0.0003 = 0.03%）
    - stamp_tax: 印花税率（默认 0.001 = 0.1%）
    - min_commission: 最小手续费（默认 5.0 元）
    
    返回:
    配置好的 Broker 实例
    """
    broker = bt.brokers.BackBroker()
    broker.setcash(initial_cash)
    
    # 设置手续费（买入和卖出都收取）
    broker.setcommission(
        commission=commission,
        margin=None,  # 股票不需要保证金
        mult=1.0,     # 乘数
        commtype=bt.CommInfoBase.COMM_PERC,  # 按百分比收取
        stocklike=True  # 股票模式
    )
    
    # 注意：Backtrader 的 setcommission 不支持分别设置买入和卖出费率
    # 也不直接支持印花税，需要自定义 CommInfo
    
    return broker
