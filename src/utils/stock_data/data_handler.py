import pandas as pd
import os
from utils.stock_data.data_source.baostock_handler import BaoStockHandler
from utils.stock_utils import get_full_code

class DataHandler:
    """
    统一数据处理入口类（单例模式）
    优化策略：
    1. 存储结构：cache_dir/{symbol}/{frequency}/{date}.parquet
    2. 按天分文件存储，方便增量更新和局部读取
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super(DataHandler, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, cache_dir: str = "local_data"):
        # 确保初始化逻辑只运行一次
        if not hasattr(self, '_initialized'):
            self.baostock_handler = BaoStockHandler()
            self.cache_dir = cache_dir
            self._initialized = True

    def _get_save_dir(self, symbol: str, frequency: str) -> str:
        """获取存储目录，不存在则创建"""
        path = os.path.join(self.cache_dir, symbol, frequency)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    def get_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjust_flag: str = "2"
    ) -> pd.DataFrame:
        """
        获取股票数据，支持按天分文件缓存
        
        逻辑：
        1. 标准化日期格式为 YYYY-MM-DD
        2. 检查本地已有文件，获取已存在的日期集合
        3. 调用 API 获取请求范围内的所有数据（只返回交易日数据）
        4. 从 API 返回的数据中提取实际存在的日期
        5. 对比找出缺失的日期，只保存缺失日期的数据
        6. 从本地读取请求范围内的所有数据并返回
        """
        # 自动补全代码前缀
        symbol = get_full_code(symbol)
        
        # 标准化日期格式为 YYYY-MM-DD，确保字符串比较正确
        start_date_normalized = pd.to_datetime(start_date).strftime('%Y-%m-%d')
        end_date_normalized = pd.to_datetime(end_date).strftime('%Y-%m-%d')
        
        save_dir = self._get_save_dir(symbol, frequency)
        
        # 1. 检查本地已有的日期文件
        existing_files = [f for f in os.listdir(save_dir) if f.endswith(".parquet")]
        existing_dates = {f.replace(".parquet", "") for f in existing_files}
        
        # 2. 调用 API 获取请求范围内的所有数据
        # 注意：API 只会返回交易日数据，不会返回周末和节假日
        # 由于我们不知道哪些是交易日，无法准确判断本地数据是否完整
        # 策略：调用 API 获取数据，然后从返回的数据中提取实际日期，只保存缺失的
        print(f"正在获取数据: {symbol} [{start_date_normalized} 到 {end_date_normalized}]")
        df_new = self.baostock_handler.get_history_k_data(
            code=symbol,
            start_date=start_date_normalized,
            end_date=end_date_normalized,
            frequency=frequency,
            adjustflag=adjust_flag
        )
        
        # 3. 从返回的数据中提取实际存在的日期，并检查哪些需要保存
        if not df_new.empty:
            # 提取日期字符串：对于日线数据索引是 date，对于分钟线数据索引是 time
            # 统一转换为 YYYY-MM-DD 格式
            if isinstance(df_new.index, pd.DatetimeIndex):
                df_new['temp_date'] = df_new.index.strftime('%Y-%m-%d')
            else:
                # 如果索引不是 DatetimeIndex，尝试转换
                df_new['temp_date'] = pd.to_datetime(df_new.index).strftime('%Y-%m-%d')
            
            # 找出需要保存的日期（API 返回的日期中，本地不存在的）
            dates_to_save = []
            for date_str, group in df_new.groupby('temp_date'):
                # 只保存缺失的日期数据
                if date_str not in existing_dates:
                    dates_to_save.append(date_str)
                    day_path = os.path.join(save_dir, f"{date_str}.parquet")
                    # 保存该日数据（移除临时列）
                    group.drop(columns=['temp_date']).to_parquet(day_path)
            
            if dates_to_save:
                print(f"已保存 {len(dates_to_save)} 个缺失日期的数据: {sorted(dates_to_save)}")
            else:
                print("所有数据已存在，无需保存新数据")
        else:
            print("API 未返回数据，可能日期范围内无交易日")

        # 4. 从本地读取最终结果
        all_dfs = []
        # 遍历目录下所有 parquet 文件
        for f in sorted(os.listdir(save_dir)):
            if f.endswith(".parquet"):
                date_str = f.replace(".parquet", "")
                # 使用标准化的日期格式进行比较
                if start_date_normalized <= date_str <= end_date_normalized:
                    file_path = os.path.join(save_dir, f)
                    all_dfs.append(pd.read_parquet(file_path))
        
        if not all_dfs:
            print(f"未找到 {symbol} 在该日期范围内的有效数据")
            return pd.DataFrame()
            
        # 合并并返回
        return pd.concat(all_dfs).sort_index()


def get_stock_data(symbol: str, start_date: str, end_date: str, frequency: str = "d") -> pd.DataFrame:
    dh = DataHandler()
    return dh.get_stock_data(symbol, start_date, end_date, frequency)

if __name__ == "__main__":
    # 测试代码
    df = get_stock_data(symbol="000651", start_date="2025-1-31", end_date="2026-12-31", frequency="5")
    
    if not df.empty:
        print(f"成功获取数据，条数: {len(df)}")
        print(df.head(100))
        
        # 检查目录结构
        # symbol_dir = os.path.join("local_data", "sz.000651", "d")
        # print(f"\n检查本地目录 {symbol_dir}:")
        # print(os.listdir(symbol_dir))

