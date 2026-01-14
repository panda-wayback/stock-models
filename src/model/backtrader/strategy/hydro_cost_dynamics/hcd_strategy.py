"""
HCD (Hydro-Cost Dynamics) 策略
基于资金能流分析的五维参数交易策略
"""
from model.backtrader.strategy.base import BaseStrategy
from model.backtrader.strategy.hydro_cost_dynamics.hcd_model import HCDModel
from datetime import date
from typing import Dict, Optional
import pandas as pd


class HCDStrategy(BaseStrategy):
    """
    HCD 量化交易策略
    
    基于五维参数体系：
    ① 水池深度 (M_pool): 主力底仓的有效堆积量
    ② 注水力度 (F_in): 多头的进攻功率
    ③ 抽水力度 (F_out): 空头的破坏功率
    ④ 水位趋势 (Trend): 资金池水位的变化方向
    ⑤ 水位偏差 (Deviation): 当前价格与能量成本的乖离率
    
    交易信号：
    - BUY: (T_rend > 0) AND (F_in > F_out) AND (D_ev < 0.3)
    - SELL: (T_rend < 0) OR (F_out > F_in * 1.5)
    """
    
    params = (
        ('printlog', False),              # 是否打印日志
        ('trigger_frequency', None),       # 触发频率
    )
    
    def __init__(self):
        """初始化策略"""
        super().__init__()
        
        # 初始化 HCD 模型（参数在模型内部定义）
        self.hcd_model = HCDModel()
        
        # 五维参数历史值（按日期存储）
        # 格式: {
        #   日期: {
        #     'm_pool': 值, 'f_in': 值, 'f_out': 值, 'trend': 值, 'deviation': 值, 'signal': 值,
        #     'cash': 资金, 'total_value': 总资产, 'position_size': 持仓数量, 
        #     'position_price': 持仓成本价, 'position_value': 持仓成本, 
        #     'position_market_value': 持仓市值, 'current_price': 当前价格
        #   }
        # }
        self.indicators_history: Dict[date, Dict[str, Optional[float]]] = {}
    
    def get_current_indicators(self) -> Optional[Dict[str, Optional[float]]]:
        """
        获取当前日期的指标值
        
        返回:
        当前日期的指标字典，如果不存在返回 None
        """
        current_date = self.data.datetime.date(0)
        return self.indicators_history.get(current_date)
    
    def get_indicator_history(self, indicator_name: str) -> Dict[date, Optional[float]]:
        """
        获取指定指标的历史值
        
        参数:
        - indicator_name: 指标名称 ('m_pool', 'f_in', 'f_out', 'trend', 'deviation', 'signal')
        
        返回:
        {日期: 值} 字典
        """
        history = {}
        for date_key, indicators in self.indicators_history.items():
            history[date_key] = indicators.get(indicator_name)
        return history
    
    def get_trigger_dataframe(self) -> pd.DataFrame:
        """
        获取触发数据源的完整 DataFrame（所有历史数据）
        
        根据 trigger_frequency 自动获取对应频率的数据：
        - 如果 trigger_frequency="d"，获取日线数据
        - 如果 trigger_frequency="5"，获取5分钟数据
        - 如果 trigger_frequency="15"，获取15分钟数据
        - 如果 trigger_frequency="60"，获取60分钟数据
        - 如果 trigger_frequency=None，使用主数据源
        
        返回:
        完整的 DataFrame，包含所有历史数据
        """
        trigger_data = self.get_trigger_data()
        
        # 如果触发数据源是主数据源，使用 get_full_dataframe()
        if trigger_data is self.data:
            return self.get_full_dataframe()
        
        # 否则，从触发数据源构建 DataFrame
        data_list = []
        current_idx = 0
        
        while current_idx < len(trigger_data.close):
            try:
                dt = trigger_data.datetime.datetime(-current_idx - 1)
                data_list.append({
                    'datetime': dt,
                    'date': dt.date(),
                    'open': trigger_data.open[-current_idx - 1],
                    'high': trigger_data.high[-current_idx - 1],
                    'low': trigger_data.low[-current_idx - 1],
                    'close': trigger_data.close[-current_idx - 1],
                    'volume': trigger_data.volume[-current_idx - 1],
                })
                current_idx += 1
            except (IndexError, AttributeError):
                break
        
        df = pd.DataFrame(data_list)
        if not df.empty:
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    def get_current_trigger_bar(self, df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, any]]:
        """
        获取当前触发数据源的当前 bar 数据（包含计算后的涨跌幅等指标）
        
        根据 trigger_frequency 获取对应频率的当前 bar：
        - 如果 trigger_frequency="d"，获取当前日线 bar
        - 如果 trigger_frequency="5"，获取当前5分钟 bar
        - 如果 trigger_frequency="15"，获取当前15分钟 bar
        - 如果 trigger_frequency="60"，获取当前60分钟 bar
        - 如果 trigger_frequency=None，使用主数据源的当前 bar
        
        参数:
        - df: 历史数据 DataFrame（用于计算相对前一日涨跌幅），可选
        
        返回:
        当前 bar 的字典，包含：
        - 基础数据：datetime, date, open, high, low, close, volume
        - 计算指标：intraday_change_pct（日内涨跌幅）, day_change_pct（日涨跌幅）, amplitude_pct（振幅）
        如果数据不存在，返回 None
        """
        trigger_data = self.get_trigger_data()
        
        try:
            open_price = trigger_data.open[0]
            high_price = trigger_data.high[0]
            low_price = trigger_data.low[0]
            close_price = trigger_data.close[0]
            volume = trigger_data.volume[0]
            dt = trigger_data.datetime.datetime(0)
            date = trigger_data.datetime.date(0)
            
            # 计算日内涨跌幅：(收盘 - 开盘) / 开盘 * 100
            intraday_change_pct = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0.0
            
            # 计算振幅：(最高 - 最低) / 开盘 * 100
            amplitude_pct = ((high_price - low_price) / open_price * 100) if open_price > 0 else 0.0
            
            # 计算相对前一日涨跌幅
            day_change_pct = None
            if df is not None and len(df) >= 2:
                prev_close = df.iloc[-2].get('close', 0) if 'close' in df.columns else None
                if prev_close and prev_close > 0:
                    day_change_pct = ((close_price - prev_close) / prev_close * 100)
            else:
                # 如果 DataFrame 不可用，尝试从触发数据源获取前一日数据
                try:
                    if len(trigger_data.close) > 1:
                        prev_close = trigger_data.close[-2]
                        if prev_close > 0:
                            day_change_pct = ((close_price - prev_close) / prev_close * 100)
                except (IndexError, AttributeError):
                    pass
            
            return {
                'datetime': dt,
                'date': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'intraday_change_pct': intraday_change_pct,  # 日内涨跌幅
                'day_change_pct': day_change_pct,  # 日涨跌幅（相对前一日）
                'amplitude_pct': amplitude_pct,  # 振幅
            }
        except (IndexError, AttributeError):
            return None
    
    def next(self):
        """策略主逻辑"""
        # 0. 检查是否应该触发（只在触发数据源更新时执行）
        if not self.should_trigger():
            return
        
        # 1. 获取触发数据源的数据（根据 trigger_frequency 自动获取对应频率的数据）
        # 如果 trigger_frequency="d"，获取日线数据
        # 如果 trigger_frequency="5"，获取5分钟数据
        # 如果 trigger_frequency="15"，获取15分钟数据
        # 如果 trigger_frequency=None，使用主数据源
        df = self.get_trigger_dataframe()  # 获取所有历史数据

        if df.empty:
            return
        
        # 可选：获取当前 bar 数据（包含计算后的涨跌幅等指标）
        current_bar = self.get_current_trigger_bar(df=df)
        if self.params.printlog and current_bar:
            # 格式化输出
            date_str = str(current_bar.get('date', 'N/A'))
            open_price = current_bar.get('open', 0)
            high_price = current_bar.get('high', 0)
            low_price = current_bar.get('low', 0)
            close_price = current_bar.get('close', 0)
            volume = current_bar.get('volume', 0)
            intraday_change_pct = current_bar.get('intraday_change_pct', 0)
            day_change_pct = current_bar.get('day_change_pct')
            amplitude_pct = current_bar.get('amplitude_pct', 0)
            
            change_sign = "+" if intraday_change_pct >= 0 else ""
            day_change_sign = "+" if day_change_pct and day_change_pct >= 0 else ""
            day_change_str = f", 日涨跌: {day_change_sign}{day_change_pct:.2f}%" if day_change_pct is not None else ""
            
            print(f"[触发数据源] 日期: {date_str}, "
                  f"开: {open_price:.2f}, "
                  f"高: {high_price:.2f}, "
                  f"低: {low_price:.2f}, "
                  f"收: {close_price:.2f}, "
                  f"日内涨跌: {change_sign}{intraday_change_pct:.2f}%"
                  f"{day_change_str}, "
                  f"振幅: {amplitude_pct:.2f}%, "
                  f"量: {volume:,.0f}") 
        
        # 2. 获取当前资金和持仓情况（模拟实盘）
        current_cash = self.broker.getcash()  # 当前可用资金
        current_value = self.broker.getvalue()  # 当前总资产（现金+持仓市值）
        position_size = self.position.size if self.position else 0  # 持仓数量
        position_price = self.position.price if self.position and position_size != 0 else 0.0  # 持仓成本价
        position_value = position_size * position_price if position_size != 0 else 0.0  # 持仓成本
        
        # 当前价格（用于计算持仓市值）
        current_price = self.get_current_price()
        position_market_value = position_size * current_price if position_size != 0 else 0.0  # 持仓市值
        
        # 3. 使用 hcd_model 计算五维参数
        indicators_df = self.hcd_model.calculate_indicators(df)
        
        # 4. 生成交易信号
        signals_df = self.hcd_model.generate_signals(indicators_df)
        
        # 安全检查：确保 signals_df 是 DataFrame
        if signals_df is None or not isinstance(signals_df, pd.DataFrame):
            return
        
        # 5. 存储到 indicators_history（按日期存储，包含资金和持仓信息）
        current_date = self.data.datetime.date(0)
        if not signals_df.empty:
            last_row = signals_df.iloc[-1]
            self.indicators_history[current_date] = {
                # 五维参数
                'm_pool': last_row.get('m_pool'),
                'f_in': last_row.get('f_in'),
                'f_out': last_row.get('f_out'),
                'trend': last_row.get('trend'),
                'deviation': last_row.get('deviation'),
                'signal': last_row.get('signal', 'WAIT'),
                # 资金和持仓信息
                'cash': current_cash,
                'total_value': current_value,
                'position_size': position_size,
                'position_price': position_price,
                'position_value': position_value,
                'position_market_value': position_market_value,
                'current_price': current_price,
            }
        
        # 6. 根据信号执行买卖操作
        current_indicators = self.get_current_indicators()
        if current_indicators:
            # TODO: 根据 signal 执行买卖操作
            # signal = current_indicators.get('signal')
            # if signal == 'BUY': ...
            # elif signal == 'SELL': ...
            pass