"""
数据适配器：将项目数据格式转换为 Backtrader 格式
"""
import pandas as pd
import backtrader as bt
from utils.stock_data import get_stock_data
from typing import Optional


def prepare_backtrader_data(
    df: pd.DataFrame,
    name: Optional[str] = None
) -> bt.feeds.PandasData:
    """
    将 DataFrame 转换为 Backtrader 的 PandasData
    
    参数:
    - df: 包含 OHLCV 数据的 DataFrame
    - name: 数据名称（可选）
    
    返回:
    Backtrader PandasData 对象
    """
    # 确保索引是 DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' in df.columns:
            df = df.set_index('date')
        else:
            df.index = pd.to_datetime(df.index)
    
    # 确保列名符合 Backtrader 要求（小写）
    column_mapping = {
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume',
    }
    
    # 重命名列
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = df[old_col]
    
    # 选择需要的列
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    available_cols = [col for col in required_cols if col in df.columns]
    
    if len(available_cols) < 4:  # 至少需要 OHLC
        raise ValueError(
            f"数据缺少必要的列，需要: {required_cols}, "
            f"实际有: {df.columns.tolist()}"
        )
    
    # 确保数据按时间排序
    df = df.sort_index()
    
    # 移除缺失值
    df = df.dropna(subset=available_cols)
    
    # 创建 Backtrader 数据源
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,  # 使用索引作为日期
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1,  # 股票不需要持仓量
    )
    
    if name:
        data._name = name
    
    return data


def load_stock_data_to_backtrader(
    symbol: str,
    start_date: str,
    end_date: str,
    frequency: str = "d",
    adjust_flag: str = "2"
) -> bt.feeds.PandasData:
    """
    从数据源加载股票数据并转换为 Backtrader 格式
    
    参数:
    - symbol: 股票代码（如 "000651"）
    - start_date: 开始日期 "YYYY-MM-DD"
    - end_date: 结束日期 "YYYY-MM-DD"
    - frequency: 数据频率 "d"=日线, "5"=5分钟等
    - adjust_flag: 复权标志 "1"=后复权, "2"=前复权, "3"=不复权
    
    返回:
    Backtrader PandasData 对象
    """
    # 获取数据
    df = get_stock_data(symbol, start_date, end_date, frequency)
    
    if df.empty:
        raise ValueError(
            f"未获取到 {symbol} 在 {start_date} 至 {end_date} 的数据"
        )
    
    # 转换为 Backtrader 格式
    data = prepare_backtrader_data(df, name=symbol)
    
    return data
