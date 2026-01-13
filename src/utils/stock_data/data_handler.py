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
        """
        # 自动补全代码前缀
        symbol = get_full_code(symbol)
        
        save_dir = self._get_save_dir(symbol, frequency)
        
        # 1. 检查本地缺失的日期
        # 注意：由于我们不确定哪些是交易日，我们先获取请求范围内已有的文件
        existing_files = [f for f in os.listdir(save_dir) if f.endswith(".parquet")]
        existing_dates = {f.replace(".parquet", "") for f in existing_files}
        
        # 生成请求范围内的日期序列（粗略检查，包含周末）
        requested_dates = pd.date_range(start=start_date, end=end_date).strftime('%Y-%m-%d').tolist()
        missing_dates = [d for d in requested_dates if d not in existing_dates]

        # 2. 如果存在缺失日期，则调用 API 下载整个范围
        # 虽然可以只下载缺失日期，但 BaoStock 范围查询更高效
        if missing_dates:
            print(f"检测到缺失数据，开始下载: {symbol} [{start_date} 到 {end_date}]")
            df_new = self.baostock_handler.get_history_k_data(
                code=symbol,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjust_flag
            )
            
            if not df_new.empty:
                # 按天拆分并保存
                # 无论索引是 date 还是 time，都统一提取出日期字符串
                df_new['temp_date'] = df_new.index.date.astype(str)
                for date_str, group in df_new.groupby('temp_date'):
                    day_path = os.path.join(save_dir, f"{date_str}.parquet")
                    # 保存该日数据
                    group.drop(columns=['temp_date']).to_parquet(day_path)
                print(f"新数据已按天保存至: {save_dir}")

        # 3. 从本地读取最终结果
        all_dfs = []
        # 遍历目录下所有 parquet 文件
        for f in sorted(os.listdir(save_dir)):
            if f.endswith(".parquet"):
                date_str = f.replace(".parquet", "")
                if start_date <= date_str <= end_date:
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
    df = get_stock_data(symbol="000651", start_date="2015-12-31", end_date="2015-12-31", frequency="5")
    
    if not df.empty:
        print(f"成功获取数据，条数: {len(df)}")
        print(df.head(100))
        
        # 检查目录结构
        # symbol_dir = os.path.join("local_data", "sz.000651", "d")
        # print(f"\n检查本地目录 {symbol_dir}:")
        # print(os.listdir(symbol_dir))

