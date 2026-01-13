"""
策略基类
提供便捷的数据访问和交易接口
"""
import backtrader as bt
from typing import List, Dict, Optional, Any
from datetime import datetime
import pandas as pd


class BaseStrategy(bt.Strategy):
    """
    策略基类
    
    提供：
    1. 便捷的数据访问方法
    2. 完整历史数据获取（DataFrame）
    3. 指标存储和管理（支持历史指标和当前指标）
    4. 日志记录
    5. T+1 限制检查
    6. 订单管理
    """
    
    params = (
        ('printlog', False),  # 是否打印日志
    )
    
    def __init__(self):
        """初始化策略"""
        # 订单引用
        self.order = None
        self.buy_order = None
        self.sell_order = None
        
        # 记录买入日期（用于 T+1 检查）
        self._buy_dates: List[datetime] = []
        
        # 数据引用
        self.datas = self.datas if hasattr(self, 'datas') else [self.data]
        self.data = self.datas[0]  # 主数据源（用于触发判断和交易）
        
        # 数据源映射：{名称: 数据源}
        self._data_map: Dict[str, bt.LineSeries] = {}
        # 初始化数据源映射（延迟初始化，在第一次访问时完成）
        self._data_map_initialized = False
        
        # 指标存储：字典结构 {指标名: {日期: 值}} 或 {指标名: 值}
        # 支持两种存储方式：
        # 1. 历史指标：{指标名: {日期: 值}} - 按日期存储历史值
        # 2. 当前指标：{指标名: 值} - 只存储当前值
        self.indicators: Dict[str, any] = {}
        
        # 完整数据缓存（DataFrame）
        self._full_dataframe: Optional[pd.DataFrame] = None
        self._dataframe_initialized: bool = False
    
    def log(self, txt: str, dt: Optional[datetime] = None, doprint: bool = False):
        """
        记录日志
        
        参数:
        - txt: 日志内容
        - dt: 日期时间（默认使用当前数据时间）
        - doprint: 是否强制打印（忽略 printlog 参数）
        """
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')
    
    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，不做处理
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                # 计算实际手续费（order.executed.comm 是总费用，但买入时只有手续费）
                commission = order.executed.comm
                self.log(
                    f'买入执行, 价格: {order.executed.price:.2f}, '
                    f'数量: {order.executed.size}, '
                    f'成本: {order.executed.value:.2f}, '
                    f'手续费: {commission:.2f}'
                )
                # 记录买入日期（用于 T+1 检查）
                self._buy_dates.append(self.data.datetime.date(0))
                self.buy_order = None
            elif order.issell():
                # 计算手续费和印花税
                # order.executed.comm 是总费用（手续费+印花税）
                total_cost = order.executed.comm
                value = abs(order.executed.size) * order.executed.price
                
                # 反推手续费和印花税
                # 手续费 = value * commission_rate，但不少于 min_commission
                # 印花税 = value * stamp_tax_rate
                # 总费用 = 手续费 + 印花税
                
                # 从 CommInfo 获取参数（需要访问 broker 的 comminfo）
                try:
                    comminfo = self.broker.getcommissioninfo(self.data)
                    commission_rate = comminfo.p.commission
                    stamp_tax_rate = comminfo.p.stamp_tax
                    min_commission = comminfo.p.min_commission
                    
                    # 计算手续费
                    commission = value * commission_rate
                    if commission < min_commission:
                        commission = min_commission
                    
                    # 计算印花税
                    stamp_tax = value * stamp_tax_rate
                    
                    self.log(
                        f'卖出执行, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, '
                        f'成本: {order.executed.value:.2f}, '
                        f'手续费: {commission:.2f}, '
                        f'印花税: {stamp_tax:.2f}, '
                        f'总费用: {total_cost:.2f}'
                    )
                except:
                    # 如果无法获取详细信息，只显示总费用
                    self.log(
                        f'卖出执行, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, '
                        f'成本: {order.executed.value:.2f}, '
                        f'总费用: {total_cost:.2f}'
                    )
                self.sell_order = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'订单 {order.status}')
        
        # 重置订单引用
        if order == self.order:
            self.order = None
        if order == self.buy_order:
            self.buy_order = None
        if order == self.sell_order:
            self.sell_order = None
    
    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return
        
        self.log(
            f'交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}'
        )
    
    def get_current_price(self) -> float:
        """获取当前价格（收盘价）"""
        return self.data.close[0]
    
    def get_current_high(self) -> float:
        """获取当前最高价"""
        return self.data.high[0]
    
    def get_current_low(self) -> float:
        """获取当前最低价"""
        return self.data.low[0]
    
    def get_current_open(self) -> float:
        """获取当前开盘价"""
        return self.data.open[0]
    
    def get_current_volume(self) -> float:
        """获取当前成交量"""
        return self.data.volume[0]
    
    def get_history_prices(self, lookback: int = 30) -> List[float]:
        """
        获取历史价格列表
        
        参数:
        - lookback: 回溯周期数
        
        返回:
        价格列表（从旧到新）
        """
        prices = []
        for i in range(lookback, -1, -1):
            if len(self.data.close) > i:
                prices.append(self.data.close[-i])
        return prices
    
    def get_history_data(self, lookback: int = 30) -> Dict[str, List]:
        """
        获取历史数据
        
        参数:
        - lookback: 回溯周期数
        
        返回:
        包含 open, high, low, close, volume, datetime 的字典
        """
        data = {
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': [],
            'datetime': []
        }
        
        for i in range(lookback, -1, -1):
            if len(self.data.close) > i:
                data['open'].append(self.data.open[-i])
                data['high'].append(self.data.high[-i])
                data['low'].append(self.data.low[-i])
                data['close'].append(self.data.close[-i])
                data['volume'].append(self.data.volume[-i])
                data['datetime'].append(self.data.datetime.datetime(-i))
        
        return data
    
    def get_full_dataframe(self) -> pd.DataFrame:
        """
        获取完整的股票数据 DataFrame
        
        返回:
        包含所有历史数据的 DataFrame，索引为日期，列为 open, high, low, close, volume
        """
        # 如果已经初始化，直接返回缓存
        if self._dataframe_initialized and self._full_dataframe is not None:
            return self._full_dataframe
        
        # 构建 DataFrame
        data_list = []
        current_idx = 0
        
        # 从最早的数据开始收集
        while current_idx < len(self.data.close):
            try:
                dt = self.data.datetime.datetime(-current_idx - 1)
                data_list.append({
                    'datetime': dt,
                    'date': dt.date(),
                    'open': self.data.open[-current_idx - 1],
                    'high': self.data.high[-current_idx - 1],
                    'low': self.data.low[-current_idx - 1],
                    'close': self.data.close[-current_idx - 1],
                    'volume': self.data.volume[-current_idx - 1],
                })
                current_idx += 1
            except (IndexError, AttributeError):
                break
        
        # 创建 DataFrame
        df = pd.DataFrame(data_list)
        if not df.empty:
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
        
        # 缓存结果
        self._full_dataframe = df
        self._dataframe_initialized = True
        
        return df
    
    def get_all_data(self) -> pd.DataFrame:
        """
        获取所有数据的别名方法（与 get_full_dataframe 相同）
        
        返回:
        完整的股票数据 DataFrame
        """
        return self.get_full_dataframe()
    
    def set_indicator(self, name: str, value: any, date: Optional[datetime] = None):
        """
        设置指标值（默认按日期存储）
        
        参数:
        - name: 指标名称（如 'chip_peak', 'rsi', 'macd' 等）
        - value: 指标值（可以是数值、列表、字典等任意类型）
        - date: 日期（可选），如果不提供则使用当前数据的日期
        
        注意：
        - 默认按日期存储，便于按时间序列获取指标
        - 如果之前存储的是非日期格式，会自动转换为日期格式
        
        示例:
        # 存储指标（自动使用当前日期）
        self.set_indicator('chip_peak', {'price': 35.5, 'volume': 1000})
        
        # 指定日期存储
        self.set_indicator('chip_peak', {'price': 35.5, 'volume': 1000}, date=self.data.datetime.date(0))
        """
        # 如果没有指定日期，使用当前数据的日期
        if date is None:
            date = self.data.datetime.date(0)
        
        # 确保指标以日期格式存储
        if name not in self.indicators:
            self.indicators[name] = {}
        elif not isinstance(self.indicators[name], dict):
            # 如果之前存储的是非字典格式，转换为日期格式
            old_value = self.indicators[name]
            self.indicators[name] = {}
            # 如果有旧值，可以保存到当前日期（可选）
            # self.indicators[name][self.data.datetime.date(0)] = old_value
        
        # 转换为日期键
        if isinstance(date, pd.Timestamp):
            date_key = date.date()
        elif isinstance(date, datetime):
            date_key = date.date()
        elif isinstance(date, str):
            date_key = pd.Timestamp(date).date()
        else:
            date_key = date
        
        # 存储指标（按日期）
        self.indicators[name][date_key] = value
    
    def get_indicator(self, name: str, date: Optional[datetime] = None, default: any = None) -> any:
        """
        获取指标值
        
        参数:
        - name: 指标名称
        - date: 日期（可选），如果提供则获取指定日期的指标，否则返回最新的指标
        - default: 默认值（如果指标不存在）
        
        返回:
        指标值，如果不存在返回 default
        
        示例:
        # 获取最新指标（当前日期或最近的日期）
        chip_peak = self.get_indicator('chip_peak')
        
        # 获取指定日期的指标
        chip_peak = self.get_indicator('chip_peak', date=self.data.datetime.date(0))
        """
        if name not in self.indicators:
            return default
        
        indicator = self.indicators[name]
        
        # 如果不是字典格式（旧格式兼容），直接返回
        if not isinstance(indicator, dict):
            return indicator
        
        if date is not None:
            # 获取指定日期的指标
            if isinstance(date, pd.Timestamp):
                date_key = date.date()
            elif isinstance(date, datetime):
                date_key = date.date()
            elif isinstance(date, str):
                date_key = pd.Timestamp(date).date()
            else:
                date_key = date
            
            return indicator.get(date_key, default)
        else:
            # 获取最新指标（最近的日期）
            if len(indicator) > 0:
                latest_date = max(indicator.keys())
                return indicator[latest_date]
            return default
    
    def get_indicator_history(self, name: str, as_list: bool = False) -> any:
        """
        获取指标的历史值（所有日期）
        
        参数:
        - name: 指标名称
        - as_list: 是否返回列表格式，默认 False 返回字典
        
        返回:
        - 如果 as_list=False: 字典 {日期: 值}，按日期排序
        - 如果 as_list=True: 列表 [(日期, 值), ...]，按日期排序
        
        示例:
        # 获取字典格式
        chip_peak_history = self.get_indicator_history('chip_peak')
        # 返回: {date1: value1, date2: value2, ...}
        
        # 获取列表格式（推荐，便于遍历）
        chip_peak_list = self.get_indicator_history('chip_peak', as_list=True)
        # 返回: [(date1, value1), (date2, value2), ...]
        for date, value in chip_peak_list:
            print(f"{date}: {value}")
        """
        if name not in self.indicators:
            return [] if as_list else {}
        
        indicator = self.indicators[name]
        
        # 如果不是字典格式（旧格式兼容），返回空
        if not isinstance(indicator, dict):
            return [] if as_list else {}
        
        if len(indicator) == 0:
            return [] if as_list else {}
        
        # 按日期排序
        sorted_items = sorted(indicator.items())
        
        if as_list:
            # 返回列表格式
            return sorted_items
        else:
            # 返回字典格式（保持排序）
            return dict(sorted_items)
    
    def has_indicator(self, name: str) -> bool:
        """
        检查指标是否存在
        
        参数:
        - name: 指标名称
        
        返回:
        - True: 指标存在
        - False: 指标不存在
        """
        return name in self.indicators
    
    def list_indicators(self) -> List[str]:
        """
        列出所有已存储的指标名称
        
        返回:
        指标名称列表
        """
        return list(self.indicators.keys())
    
    def clear_indicator(self, name: Optional[str] = None):
        """
        清除指标
        
        参数:
        - name: 指标名称，如果为 None 则清除所有指标
        """
        if name is None:
            self.indicators.clear()
        elif name in self.indicators:
            del self.indicators[name]
    
    def _init_data_map(self):
        """初始化数据源映射"""
        if not self._data_map_initialized:
            for i, data in enumerate(self.datas):
                name = getattr(data, '_name', f'data_{i}')
                self._data_map[name] = data
            self._data_map_initialized = True
    
    def get_data(self, name: Optional[str] = None) -> bt.LineSeries:
        """
        获取指定名称的数据源
        
        参数:
        - name: 数据源名称（如 "000651_d", "000651_60", "000651_w"）
               如果为 None，返回主数据源
        
        返回:
        数据源对象
        
        示例:
        # 获取日线数据
        daily_data = self.get_data("000651_d")
        daily_price = daily_data.close[0]
        
        # 获取周线数据
        weekly_data = self.get_data("000651_w")
        weekly_price = weekly_data.close[0]
        """
        # 初始化数据源映射
        self._init_data_map()
        
        if name is None:
            return self.data
        
        if name in self._data_map:
            return self._data_map[name]
        
        # 如果名称不存在，尝试通过索引访问
        try:
            idx = int(name)
            if 0 <= idx < len(self.datas):
                return self.datas[idx]
        except (ValueError, IndexError):
            pass
        
        raise ValueError(f"数据源 '{name}' 不存在。可用数据源: {list(self._data_map.keys())}")
    
    def get_dataframe(self, name: Optional[str] = None) -> pd.DataFrame:
        """
        获取指定数据源的完整 DataFrame
        
        参数:
        - name: 数据源名称，如果为 None 则使用主数据源
        
        返回:
        完整的 DataFrame
        """
        data = self.get_data(name)
        
        # 构建 DataFrame
        data_list = []
        current_idx = 0
        
        while current_idx < len(data.close):
            try:
                dt = data.datetime.datetime(-current_idx - 1)
                data_list.append({
                    'datetime': dt,
                    'date': dt.date(),
                    'open': data.open[-current_idx - 1],
                    'high': data.high[-current_idx - 1],
                    'low': data.low[-current_idx - 1],
                    'close': data.close[-current_idx - 1],
                    'volume': data.volume[-current_idx - 1],
                })
                current_idx += 1
            except (IndexError, AttributeError):
                break
        
        df = pd.DataFrame(data_list)
        if not df.empty:
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    def list_data_sources(self) -> List[str]:
        """
        列出所有可用的数据源名称
        
        返回:
        数据源名称列表
        """
        self._init_data_map()
        return list(self._data_map.keys())
    
    def can_sell_today(self) -> bool:
        """
        检查今天是否可以卖出（T+1 限制）
        
        返回:
        - True: 可以卖出
        - False: 不能卖出（今天有买入）
        """
        if not self.position or self.position.size <= 0:
            return True  # 没有持仓，可以卖出（做空场景，但A股不支持）
        
        current_date = self.data.datetime.date(0)
        return current_date not in self._buy_dates
    
    def buy(self, size: Optional[float] = None, price: Optional[float] = None,
            exectype: Optional[int] = None,
            valid: Optional[datetime] = None, tradeid: int = 0,
            **kwargs):
        """
        买入（重写以支持 T+1 检查）
        
        参数:
        - size: 买入数量，如果为 None 则使用全部现金买入
        - 其他参数同 Backtrader 的 buy() 方法
        """
        # 如果有未完成的订单，不重复下单
        if self.order:
            return None
        
        # 如果未指定数量，使用全部现金买入
        if size is None:
            size = self.calculate_position_size(cash_ratio=1.0)
            if size <= 0:
                return None
        
        # 执行买入
        self.order = super().buy(
            size=size, price=price, exectype=exectype,
            valid=valid, tradeid=tradeid, **kwargs
        )
        self.buy_order = self.order
        return self.order
    
    def sell(self, size: Optional[float] = None, price: Optional[float] = None,
             exectype: Optional[int] = None,
             valid: Optional[datetime] = None, tradeid: int = 0,
             **kwargs):
        """
        卖出（重写以支持 T+1 检查）
        
        参数:
        - size: 卖出数量，如果为 None 则卖出全部持仓
        - 其他参数同 Backtrader 的 sell() 方法
        """
        # 如果有未完成的订单，不重复下单
        if self.order:
            return None
        
        # 检查 T+1 限制
        if not self.can_sell_today():
            self.log('今天有买入，不能卖出（T+1限制）', doprint=True)
            return None
        
        # 如果未指定数量，卖出全部持仓
        if size is None:
            if self.position and self.position.size > 0:
                size = abs(self.position.size)
            else:
                return None
        
        # 执行卖出
        self.order = super().sell(
            size=size, price=price, exectype=exectype,
            valid=valid, tradeid=tradeid, **kwargs
        )
        self.sell_order = self.order
        return self.order
    
    def close(self, **kwargs):
        """平仓"""
        return self.sell(size=self.position.size, **kwargs)
    
    def calculate_position_size(self, 
                                cash_ratio: float = 1.0,
                                position_ratio: Optional[float] = None,
                                fixed_size: Optional[int] = None,
                                min_size: int = 100) -> int:
        """
        计算买入/卖出数量
        
        参数:
        - cash_ratio: 使用现金的比例（0.0-1.0），如 0.5 表示使用50%的现金
        - position_ratio: 使用持仓的比例（0.0-1.0），如 0.5 表示卖出50%的持仓
        - fixed_size: 固定数量（股数），如果指定则优先使用
        - min_size: 最小交易数量（默认100股，即1手）
        
        返回:
        计算后的数量（已按最小交易单位取整）
        
        示例:
        # 使用50%现金买入
        size = self.calculate_position_size(cash_ratio=0.5)
        self.buy(size=size)
        
        # 卖出50%持仓
        size = self.calculate_position_size(position_ratio=0.5)
        self.sell(size=size)
        
        # 固定买入1000股
        size = self.calculate_position_size(fixed_size=1000)
        self.buy(size=size)
        """
        if fixed_size is not None:
            # 固定数量
            size = fixed_size
        elif position_ratio is not None:
            # 按持仓比例卖出
            if not self.position or self.position.size <= 0:
                return 0
            size = int(abs(self.position.size) * position_ratio)
        else:
            # 按现金比例买入
            cash = self.broker.getcash()
            price = self.get_current_price()
            if price <= 0:
                return 0
            
            # 计算可用资金
            available_cash = cash * cash_ratio
            
            # 计算可买数量
            size = int(available_cash / price)
        
        # 按最小交易单位取整（A股是100股为1手）
        size = (size // min_size) * min_size
        
        return max(0, size)  # 确保非负
    
    def buy_with_ratio(self, cash_ratio: float = 1.0, **kwargs):
        """
        按现金比例买入
        
        参数:
        - cash_ratio: 使用现金的比例（0.0-1.0）
        - **kwargs: 传递给 buy() 的其他参数
        
        示例:
        # 使用50%现金买入
        self.buy_with_ratio(cash_ratio=0.5)
        
        # 使用全部现金买入
        self.buy_with_ratio(cash_ratio=1.0)
        """
        size = self.calculate_position_size(cash_ratio=cash_ratio)
        if size > 0:
            return self.buy(size=size, **kwargs)
        return None
    
    def sell_with_ratio(self, position_ratio: float = 1.0, **kwargs):
        """
        按持仓比例卖出
        
        参数:
        - position_ratio: 卖出持仓的比例（0.0-1.0），1.0表示全部卖出
        - **kwargs: 传递给 sell() 的其他参数
        
        示例:
        # 卖出50%持仓
        self.sell_with_ratio(position_ratio=0.5)
        
        # 全部卖出（等同于 close()）
        self.sell_with_ratio(position_ratio=1.0)
        """
        size = self.calculate_position_size(position_ratio=position_ratio)
        if size > 0:
            return self.sell(size=size, **kwargs)
        return None
    
    def next(self):
        """
        策略主逻辑（子类必须实现）
        """
        raise NotImplementedError("子类必须实现 next() 方法")
