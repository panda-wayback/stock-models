"""
定时触发机制
基于时间条件触发交易信号
"""
from typing import Optional, List, Callable
from datetime import datetime, time
import backtrader as bt


class TimeTrigger:
    """
    定时触发器
    
    用于在特定时间点触发交易信号
    """
    
    def __init__(self, name: str = "TimeTrigger"):
        """
        初始化定时触发器
        
        参数:
        - name: 触发器名称
        """
        self.name = name
        self.triggers: List[Dict] = []
    
    def add_daily_trigger(
        self,
        trigger_time: time,
        callback: Callable,
        description: str = ""
    ):
        """
        添加每日定时触发
        
        参数:
        - trigger_time: 触发时间（如 time(9, 30) 表示 9:30）
        - callback: 回调函数
        - description: 描述
        """
        self.triggers.append({
            'type': 'daily',
            'time': trigger_time,
            'callback': callback,
            'description': description,
            'last_trigger_date': None
        })
    
    def add_weekly_trigger(
        self,
        weekday: int,
        trigger_time: time,
        callback: Callable,
        description: str = ""
    ):
        """
        添加每周定时触发
        
        参数:
        - weekday: 星期几（0=周一, 6=周日）
        - trigger_time: 触发时间
        - callback: 回调函数
        - description: 描述
        """
        self.triggers.append({
            'type': 'weekly',
            'weekday': weekday,
            'time': trigger_time,
            'callback': callback,
            'description': description,
            'last_trigger_date': None
        })
    
    def check_and_trigger(self, current_datetime: datetime):
        """
        检查并触发定时任务
        
        参数:
        - current_datetime: 当前日期时间
        """
        current_time = current_datetime.time()
        current_weekday = current_datetime.weekday()
        current_date = current_datetime.date()
        
        for trigger in self.triggers:
            should_trigger = False
            
            if trigger['type'] == 'daily':
                # 每日触发：检查时间是否匹配
                if (current_time >= trigger['time'] and
                    trigger['last_trigger_date'] != current_date):
                    should_trigger = True
            
            elif trigger['type'] == 'weekly':
                # 每周触发：检查星期和时间是否匹配
                if (current_weekday == trigger['weekday'] and
                    current_time >= trigger['time'] and
                    trigger['last_trigger_date'] != current_date):
                    should_trigger = True
            
            if should_trigger:
                trigger['last_trigger_date'] = current_date
                trigger['callback'](current_datetime)
    
    def reset(self):
        """重置所有触发器的最后触发日期"""
        for trigger in self.triggers:
            trigger['last_trigger_date'] = None


class TradingHoursTrigger:
    """
    交易时间触发器
    
    用于在交易时间段内触发信号
    """
    
    # A股交易时间
    MORNING_START = time(9, 30)
    MORNING_END = time(11, 30)
    AFTERNOON_START = time(13, 0)
    AFTERNOON_END = time(15, 0)
    
    def __init__(self):
        """初始化交易时间触发器"""
        self.is_trading_hours = False
        self.is_morning_session = False
        self.is_afternoon_session = False
    
    def check_trading_hours(self, current_time: time) -> bool:
        """
        检查是否在交易时间内
        
        参数:
        - current_time: 当前时间
        
        返回:
        - True: 在交易时间内
        """
        morning = self.MORNING_START <= current_time <= self.MORNING_END
        afternoon = self.AFTERNOON_START <= current_time <= self.AFTERNOON_END
        
        self.is_trading_hours = morning or afternoon
        self.is_morning_session = morning
        self.is_afternoon_session = afternoon
        
        return self.is_trading_hours
    
    def is_in_morning_session(self, current_time: time) -> bool:
        """检查是否在上午交易时段"""
        return self.MORNING_START <= current_time <= self.MORNING_END
    
    def is_in_afternoon_session(self, current_time: time) -> bool:
        """检查是否在下午交易时段"""
        return self.AFTERNOON_START <= current_time <= self.AFTERNOON_END
