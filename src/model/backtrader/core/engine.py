"""
Backtrader 回测引擎
提供统一的回测接口
"""
import backtrader as bt
from typing import Optional, Dict, Any, Type, List, List
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
        
        # 数据源配置
        self._data_sources_added = False
    
    def add_data(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "d",
        df: Optional[pd.DataFrame] = None,
        name: Optional[str] = None,
        is_main: bool = False
    ):
        """
        添加数据源（支持多数据源）
        
        方式1：从数据源加载
        - symbol: 股票代码
        - start_date: 开始日期
        - end_date: 结束日期
        - frequency: 数据频率（"d"=日线, "60"=60分钟, "w"=周线等）
        - is_main: 是否为主数据源（用于触发判断，默认False，第一个添加的自动成为主数据源）
        
        方式2：直接传入 DataFrame
        - df: 包含 OHLCV 的 DataFrame
        - name: 数据名称（可选，用于标识数据源）
        - is_main: 是否为主数据源
        
        注意：
        - 第一个添加的数据源自动成为主数据源（用于触发判断）
        - 如果指定 is_main=True，该数据源会成为主数据源
        - 主数据源用于 next() 的触发和交易执行
        """
        if df is not None:
            # 使用提供的 DataFrame
            data = prepare_backtrader_data(df, name=name or symbol or f"data_{len(self.cerebro.datas)}")
        elif symbol and start_date and end_date:
            # 从数据源加载
            data = load_stock_data_to_backtrader(
                symbol, start_date, end_date, frequency
            )
            # 设置数据名称（包含频率信息）
            if name is None:
                name = f"{symbol}_{frequency}"
            data._name = name
        else:
            raise ValueError("必须提供 DataFrame 或 (symbol, start_date, end_date)")
        
        # 添加数据源到 Cerebro
        # Backtrader 会自动处理主数据源和辅助数据源的同步
        self.cerebro.adddata(data)
        
        return self
    
    def add_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        frequencies: Optional[List[str]] = None,
        main_frequency: Optional[str] = None
    ):
        """
        自动添加股票的所有数据源（一键添加）
        
        参数:
        - symbol: 股票代码（如 "000651"）
        - start_date: 开始日期 "YYYY-MM-DD"
        - end_date: 结束日期 "YYYY-MM-DD"
        - frequencies: 需要的数据频率列表，默认 ["5", "15", "30", "60", "d"]
                     支持: "5", "15", "30", "60" (分钟线), "d" (日线), "w" (周线), "m" (月线)
        - main_frequency: 主数据源频率（用于触发判断），默认 "5"（5分钟线）
                         如果 frequencies 中没有该频率，会自动添加
        
        返回:
        self（支持链式调用）
        
        示例:
        # 自动添加所有数据源（5分钟、15分钟、30分钟、60分钟、日线）
        engine.add_stock_data("000651", "2025-01-01", "2025-12-31")
        
        # 只添加日线和周线
        engine.add_stock_data(
            "000651", 
            "2025-01-01", 
            "2025-12-31",
            frequencies=["d", "w"]
        )
        
        # 指定主数据源为日线
        engine.add_stock_data(
            "000651",
            "2025-01-01",
            "2025-12-31",
            main_frequency="d"
        )
        """
        if frequencies is None:
            frequencies = ["5", "15", "30", "60", "d"]  # 默认：所有分钟线（5、15、30、60分钟）和日线
        
        if main_frequency is None:
            main_frequency = "5"  # 默认主数据源：5分钟线（最细粒度，用于精确触发）
        
        # 确保主数据源在频率列表中，并且是第一个
        if main_frequency not in frequencies:
            frequencies.insert(0, main_frequency)
        else:
            # 如果主数据源在列表中，移到第一个位置
            frequencies.remove(main_frequency)
            frequencies.insert(0, main_frequency)
        
        # 频率名称映射
        frequency_names = {
            "5": "5分钟",
            "15": "15分钟",
            "30": "30分钟",
            "60": "60分钟",
            "d": "日线",
            "w": "周线",
            "m": "月线"
        }
        
        # 添加每个数据源
        for i, freq in enumerate(frequencies):
            is_main = (i == 0)  # 第一个数据源是主数据源
            name = f"{symbol}_{freq}"
            
            if self.printlog:
                freq_name = frequency_names.get(freq, freq)
                main_tag = "（主数据源）" if is_main else ""
                print(f"正在添加 {symbol} 的 {freq_name} 数据{main_tag}...")
            
            self.add_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                frequency=freq,
                name=name,
                is_main=is_main
            )
        
        self._data_sources_added = True
        
        if self.printlog:
            print(f"✓ 已添加 {len(frequencies)} 个数据源")
        
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
