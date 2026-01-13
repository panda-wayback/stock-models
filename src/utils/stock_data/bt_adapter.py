import backtrader as bt
import pandas as pd
from utils.stock_data.data_handler import get_stock_data

class PandasDataPlus(bt.feeds.PandasData):
    """
    自定义 Backtrader Pandas 数据类
    支持更多字段（如成交额等）
    """
    lines = ('amount', 'turn',)
    params = (
        ('amount', -1),  # 成交额
        ('turn', -1),    # 换手率
    )

def load_data_to_bt(symbol, start_date, end_date, frequency='d'):
    """
    将 DataHandler 获取的数据转换为 Backtrader DataFeed
    """
    df = get_stock_data(symbol, start_date, end_date, frequency)
    
    if df.empty:
        return None
        
    # Backtrader 需要列名匹配或指定
    # 默认列：open, high, low, close, volume, openinterest
    # 注意：BaoStock 返回的列名已经是 open, high, low, close, volume 等
    
    data = PandasDataPlus(
        dataname=df,
        datetime=None,  # 使用 index 作为 datetime
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        amount='amount',
        turn='turn',
        openinterest=-1
    )
    
    return data
