"""
HCD (Hydro-Cost Dynamics) 模型
基于资金能流分析的五维参数计算模型
"""
import pandas as pd


class HCDModel:
    """
    HCD 量化模型主类
    
    核心功能：
    1. 计算五维参数体系
    2. 生成交易信号
    
    五维参数：
    ① 水池深度 (M_pool): 主力底仓的有效堆积量
    ② 注水力度 (F_in): 多头的进攻功率
    ③ 抽水力度 (F_out): 空头的破坏功率
    ④ 水位趋势 (Trend): 资金池水位的变化方向
    ⑤ 水位偏差 (Deviation): 当前价格与能量成本的乖离率
    """
    
    def __init__(
        self,
        window: int = 20,
        decay_factor: float = 0.99,
        coverage_coefficient: float = 1.2,
        max_deviation: float = 0.3
    ):
        """
        初始化 HCD 模型
        
        参数:
        - window: 计算窗口大小，默认 20
        - decay_factor: 水池深度衰减因子，默认 0.99
        - coverage_coefficient: 覆盖原则系数，默认 1.2
        - max_deviation: 最大水位偏差（乖离率），默认 0.3（30%）
        """
        self.window = window
        self.decay_factor = decay_factor
        self.coverage_coefficient = coverage_coefficient
        self.max_deviation = max_deviation
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算五维参数体系
        
        输入:
        - df: DataFrame，必须包含列：['open', 'high', 'low', 'close', 'volume']
        
        输出:
        - DataFrame，新增以下列：
            - 'm_pool': 水池深度 (Pool Depth) - ①
            - 'f_in': 注水力度 (Injection Force) - ②
            - 'f_out': 抽水力度 (Extraction Force) - ③
            - 'trend': 水位趋势 (Trend) - ④
            - 'deviation': 水位偏差 (Deviation) - ⑤
        """
        if df.empty:
            return df.copy()
        
        # 确保索引是连续的（用于 shift 操作）
        df = df.copy().reset_index(drop=True)
        
        # 1. 计算资金能流 (MEF) = Volume * (Close - Open) / Open
        df['mef'] = df['volume'] * (df['close'] - df['open']) / df['open']
        
        # 2. 计算注水流量和抽水流量
        df['flow_in'] = df['mef'].where(df['mef'] > 0, 0)  # 正能流 = 注水
        df['flow_out'] = df['mef'].where(df['mef'] < 0, 0)  # 负能流 = 抽水
        
        # 3. 计算水池深度 (M_pool) = 累积求和 (flow_in - flow_out)，带衰减因子
        net_flow = df['flow_in'] + df['flow_out']  # flow_out 已经是负数
        # 应用衰减因子：每个周期衰减一次（向量化计算）
        df['m_pool'] = net_flow.copy()
        for i in range(1, len(df)):
            df.loc[i, 'm_pool'] = df.loc[i-1, 'm_pool'] * self.decay_factor + net_flow.iloc[i]
        
        # 4. 计算注水力度 (F_in) = 正 flow_in 的滚动平均
        df['f_in'] = df['flow_in'].rolling(window=self.window, min_periods=1).mean()
        
        # 5. 计算抽水力度 (F_out) = 负 flow_out 的绝对值的滚动平均
        df['f_out'] = (-df['flow_out']).rolling(window=self.window, min_periods=1).mean()
        
        # 6. 计算水位趋势 (Trend) = m_pool - m_pool.shift(N)
        df['trend'] = df['m_pool'] - df['m_pool'].shift(self.window).fillna(0)
        
        # 7. 计算水位偏差 (Deviation) = (close - vwap) / vwap
        # VWAP = 成交量加权平均价
        df['vwap'] = (df['close'] * df['volume']).rolling(window=self.window, min_periods=1).sum() / df['volume'].rolling(window=self.window, min_periods=1).sum()
        df['deviation'] = (df['close'] - df['vwap']) / df['vwap']
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        输入:
        - df: DataFrame，必须包含计算后的指标列
        
        输出:
        - DataFrame，新增 'signal' 列：
            - 'BUY': 买入信号
            - 'SELL': 卖出信号
            - 'WAIT': 观望信号
        
        判定逻辑：
        - BUY: (T_rend > 0) AND (F_in > F_out) AND (D_ev < 0.3)
        - SELL: (T_rend < 0) OR (F_out > F_in * 1.5)
        """
        if df.empty:
            df = df.copy()
            df['signal'] = 'WAIT'
            return df
        
        df = df.copy()
        
        # 初始化信号列为 WAIT
        df['signal'] = 'WAIT'
        
        # 填充 NaN 值，避免条件判断出错
        df['trend'] = df['trend'].fillna(0)
        df['f_in'] = df['f_in'].fillna(0)
        df['f_out'] = df['f_out'].fillna(0)
        df['deviation'] = df['deviation'].fillna(0)
        
        # 买入条件：趋势向上 AND 注水力度大于抽水力度 AND 偏差小于阈值
        buy_condition = (
            (df['trend'] > 0) &
            (df['f_in'] > df['f_out']) &
            (df['deviation'].abs() < self.max_deviation)
        )
        df.loc[buy_condition, 'signal'] = 'BUY'
        
        # 卖出条件：趋势向下 OR 抽水力度过大
        sell_condition = (
            (df['trend'] < 0) |
            (df['f_out'] > df['f_in'] * 1.5)
        )
        df.loc[sell_condition, 'signal'] = 'SELL'
        
        return df