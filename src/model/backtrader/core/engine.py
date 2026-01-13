"""
Backtrader 回测引擎
提供统一的回测接口
"""
import backtrader as bt
from typing import Optional, Dict, Any, Type
from datetime import datetime
import pandas as pd

from model.backtrader.core.data_adapter import load_stock_data_to_backtrader, prepare_backtrader_data
from model.backtrader.core.comm_info import ChinaStockCommInfo


class BacktestEngine:
    """
    Backtrader 回测引擎
    
    封装 Backtrader 的 Cerebro，提供简洁的接口
    """
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission: float = 0.0003,
        stamp_tax: float = 0.001,
        min_commission: float = 5.0,
        printlog: bool = False
    ):
        """
        初始化回测引擎
        
        参数:
        - initial_cash: 初始资金
        - commission: 手续费率（默认 0.0003 = 0.03%）
        - stamp_tax: 印花税率（默认 0.001 = 0.1%）
        - min_commission: 最小手续费（默认 5.0 元）
        - printlog: 是否打印日志
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        self.printlog = printlog
        
        # 创建 Cerebro
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金
        self.cerebro.broker.setcash(initial_cash)
        
        # 设置手续费和印花税
        comminfo = ChinaStockCommInfo(
            commission=commission,
            stamp_tax=stamp_tax,
            min_commission=min_commission
        )
        self.cerebro.broker.addcommissioninfo(comminfo)
        
        # 设置其他参数
        self.cerebro.broker.set_coc(True)  # 允许收盘价成交
    
    def add_data(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "d",
        df: Optional[pd.DataFrame] = None,
        name: Optional[str] = None
    ):
        """
        添加数据源
        
        方式1：从数据源加载
        - symbol: 股票代码
        - start_date: 开始日期
        - end_date: 结束日期
        - frequency: 数据频率
        
        方式2：直接传入 DataFrame
        - df: 包含 OHLCV 的 DataFrame
        - name: 数据名称（可选）
        """
        if df is not None:
            # 使用提供的 DataFrame
            data = prepare_backtrader_data(df, name=name or symbol)
        elif symbol and start_date and end_date:
            # 从数据源加载
            data = load_stock_data_to_backtrader(
                symbol, start_date, end_date, frequency
            )
        else:
            raise ValueError("必须提供 DataFrame 或 (symbol, start_date, end_date)")
        
        self.cerebro.adddata(data)
        return self
    
    def add_strategy(
        self,
        strategy_class: Type[bt.Strategy],
        **strategy_params
    ):
        """
        添加策略
        
        参数:
        - strategy_class: 策略类（继承自 bt.Strategy）
        - **strategy_params: 策略参数
        """
        self.cerebro.addstrategy(strategy_class, **strategy_params)
        return self
    
    def add_analyzer(self, analyzer_class: Type[bt.Analyzer], **analyzer_params):
        """
        添加分析器
        
        参数:
        - analyzer_class: 分析器类
        - **analyzer_params: 分析器参数
        """
        self.cerebro.addanalyzer(analyzer_class, **analyzer_params)
        return self
    
    def add_observer(self, observer_class: Type[bt.Observer], **observer_params):
        """
        添加观察者
        
        参数:
        - observer_class: 观察者类
        - **observer_params: 观察者参数
        """
        self.cerebro.addobserver(observer_class, **observer_params)
        return self
    
    def run(self) -> Dict[str, Any]:
        """
        运行回测
        
        返回:
        回测结果字典
        """
        if self.printlog:
            print("=" * 60)
            print("开始回测")
            print("=" * 60)
            print(f"初始资金: {self.initial_cash:,.2f}")
            print(f"手续费率: {self.commission*100:.3f}%")
            print(f"印花税率: {self.stamp_tax*100:.2f}%")
            print("=" * 60)
        
        # 运行回测
        strategies = self.cerebro.run()
        
        # 获取结果
        strategy = strategies[0]
        
        # 获取最终资金
        final_value = self.cerebro.broker.getvalue()
        
        # 计算收益率
        total_return = (final_value - self.initial_cash) / self.initial_cash * 100
        
        result = {
            'initial_cash': self.initial_cash,
            'final_value': final_value,
            'total_return': total_return,
            'strategy': strategy
        }
        
        # 如果有分析器，添加分析结果
        if hasattr(strategy, 'analyzers'):
            for analyzer in strategy.analyzers:
                result[analyzer.__class__.__name__] = analyzer.get_analysis()
        
        if self.printlog:
            print("\n" + "=" * 60)
            print("回测结果")
            print("=" * 60)
            print(f"初始资金: {result['initial_cash']:,.2f}")
            print(f"最终资金: {result['final_value']:,.2f}")
            print(f"总收益率: {result['total_return']:.2f}%")
            print("=" * 60)
        
        return result
    
    def plot(self, **kwargs):
        """
        绘制回测结果图表
        
        参数:
        - **kwargs: 传递给 cerebro.plot() 的参数
        """
        self.cerebro.plot(**kwargs)
    
    def get_cerebro(self) -> bt.Cerebro:
        """
        获取底层的 Cerebro 对象（用于高级用法）
        """
        return self.cerebro
