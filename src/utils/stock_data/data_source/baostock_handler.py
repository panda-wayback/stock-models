import baostock as bs
import pandas as pd
from panda_python_packages import singleton

@singleton
class BaoStockHandler:
    """
    BaoStock 数据获取封装类 (单例模式)
    """
    def get_history_k_data(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "2"
    ) -> pd.DataFrame:
        """
        获取历史K线数据
        
        参数:
        - code: 股票代码，格式如 "sh.600000" 或 "sz.000001"
        - start_date: 开始日期，格式 "YYYY-MM-DD"
        - end_date: 结束日期，格式 "YYYY-MM-DD"
        - frequency: 数据周期，d=日k线、w=周、m=月、5=5分钟、15=15分钟、30=30分钟、60=60分钟
        - adjustflag: 复权类型，1:后复权 2:前复权 3:不复权 (默认2)
        
        返回:
        - pd.DataFrame: 包含K线数据的 DataFrame
        """
        
        # 1. 登录系统
        lg = bs.login()
        if lg.error_code != '0':
            raise Exception(f"BaoStock 登录失败: {lg.error_msg}")

        try:
            # 2. 确定查询字段
            # 日线、周线、月线包含更多财务指标字段；分钟线字段相对较少
            if frequency in ['d', 'w', 'm']:
                fields = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
            else:
                # 分钟线增加 time 字段，暂不支持财务指标
                fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"

            # 3. 获取历史K线数据
            rs = bs.query_history_k_data_plus(
                code,
                fields,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjustflag
            )

            if rs.error_code != '0':
                raise Exception(f"获取数据失败: {rs.error_msg}")

            # 4. 转化为 DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            df = pd.DataFrame(data_list, columns=rs.fields)

            # 5. 数据清洗与类型转换
            if not df.empty:
                # 定义需要转换为数值型的列
                numeric_cols = [
                    'open', 'high', 'low', 'close', 'volume', 'amount', 
                    'preclose', 'pctChg', 'turn', 'peTTM', 'pbMRQ', 'psTTM', 'pcfNcfTTM'
                ]
                
                # 过滤出 DataFrame 中实际存在的数值列
                existing_numeric_cols = [col for col in numeric_cols if col in df.columns]
                df[existing_numeric_cols] = df[existing_numeric_cols].apply(pd.to_numeric, errors='coerce')

                # 时间处理
                if 'time' in df.columns:
                    # 分钟数据：20230101140500000 -> datetime
                    df['time'] = pd.to_datetime(df['time'], format='%Y%m%d%H%M%S%f')
                    df.set_index('time', inplace=True)
                elif 'date' in df.columns:
                    # 日线数据：2023-01-01 -> datetime
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)

            return df

        finally:
            # 6. 登出系统
            bs.logout()

if __name__ == "__main__":
    # 测试代码
    handler = BaoStockHandler()
    # 获取格力电器日线数据
    test_df = handler.get_history_k_data(
        code="sz.000651",
        start_date="2015-01-01",
        end_date="2015-01-02",
        frequency="d"
    )
    print("日线数据预览:")
    print(test_df.head())
    
    # 获取格力电器5分钟线数据
    test_min_df = handler.get_history_k_data(
        code="sz.000651",
        start_date="2015-01-01",
        end_date="2015-01-05",
        frequency="60"
    )
    print("\n5分钟线数据预览:")
    print(test_min_df.head())

