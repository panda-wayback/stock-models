"""
信号触发机制
基于技术指标或自定义条件触发交易信号
"""
from typing import Callable, Optional, Dict, Any
import backtrader as bt


class SignalTrigger:
    """
    信号触发器
    
    用于在策略中基于条件触发交易信号
    """
    
    def __init__(self, name: str = "SignalTrigger"):
        """
        初始化信号触发器
        
        参数:
        - name: 触发器名称
        """
        self.name = name
        self.signals: Dict[str, Callable] = {}
        self.signal_states: Dict[str, bool] = {}
    
    def register_signal(
        self,
        signal_name: str,
        condition_func: Callable[[], bool],
        initial_state: bool = False
    ):
        """
        注册信号
        
        参数:
        - signal_name: 信号名称
        - condition_func: 条件函数，返回 True 表示信号触发
        - initial_state: 初始状态
        """
        self.signals[signal_name] = condition_func
        self.signal_states[signal_name] = initial_state
    
    def check_signal(self, signal_name: str) -> bool:
        """
        检查信号是否触发
        
        参数:
        - signal_name: 信号名称
        
        返回:
        - True: 信号触发
        - False: 信号未触发
        """
        if signal_name not in self.signals:
            return False
        
        condition_func = self.signals[signal_name]
        current_state = condition_func()
        
        # 检测信号变化（从 False 变为 True）
        previous_state = self.signal_states[signal_name]
        self.signal_states[signal_name] = current_state
        
        # 返回是否刚刚触发（上升沿）
        return current_state and not previous_state
    
    def is_signal_active(self, signal_name: str) -> bool:
        """
        检查信号是否处于激活状态
        
        参数:
        - signal_name: 信号名称
        
        返回:
        - True: 信号激活
        - False: 信号未激活
        """
        if signal_name not in self.signals:
            return False
        
        return self.signal_states.get(signal_name, False)
    
    def reset(self):
        """重置所有信号状态"""
        for signal_name in self.signal_states:
            self.signal_states[signal_name] = False


class CrossoverSignal:
    """
    交叉信号触发器
    
    用于检测两条线的交叉（金叉/死叉）
    """
    
    def __init__(self, fast_line, slow_line):
        """
        初始化交叉信号
        
        参数:
        - fast_line: 快线（如短期均线）
        - slow_line: 慢线（如长期均线）
        """
        self.fast_line = fast_line
        self.slow_line = slow_line
        self.last_fast = None
        self.last_slow = None
    
    def check_golden_cross(self) -> bool:
        """
        检查是否出现金叉（快线上穿慢线）
        
        返回:
        - True: 出现金叉
        """
        if len(self.fast_line) < 2 or len(self.slow_line) < 2:
            return False
        
        current_fast = self.fast_line[0]
        current_slow = self.slow_line[0]
        prev_fast = self.fast_line[-1]
        prev_slow = self.slow_line[-1]
        
        # 金叉：快线从下方穿越到上方
        golden_cross = (
            prev_fast <= prev_slow and
            current_fast > current_slow
        )
        
        return golden_cross
    
    def check_death_cross(self) -> bool:
        """
        检查是否出现死叉（快线下穿慢线）
        
        返回:
        - True: 出现死叉
        """
        if len(self.fast_line) < 2 or len(self.slow_line) < 2:
            return False
        
        current_fast = self.fast_line[0]
        current_slow = self.slow_line[0]
        prev_fast = self.fast_line[-1]
        prev_slow = self.slow_line[-1]
        
        # 死叉：快线从上方穿越到下方
        death_cross = (
            prev_fast >= prev_slow and
            current_fast < current_slow
        )
        
        return death_cross


class ThresholdSignal:
    """
    阈值信号触发器
    
    用于检测指标是否超过/低于阈值
    """
    
    def __init__(self, indicator, threshold: float, above: bool = True):
        """
        初始化阈值信号
        
        参数:
        - indicator: 指标（如 RSI、价格等）
        - threshold: 阈值
        - above: True 表示超过阈值触发，False 表示低于阈值触发
        """
        self.indicator = indicator
        self.threshold = threshold
        self.above = above
        self.last_state = False
    
    def check(self) -> bool:
        """
        检查是否触发
        
        返回:
        - True: 信号触发（上升沿）
        """
        if len(self.indicator) < 1:
            return False
        
        current_value = self.indicator[0]
        
        if self.above:
            current_state = current_value > self.threshold
        else:
            current_state = current_value < self.threshold
        
        # 检测上升沿
        triggered = current_state and not self.last_state
        self.last_state = current_state
        
        return triggered
    
    def is_active(self) -> bool:
        """
        检查信号是否处于激活状态
        
        返回:
        - True: 信号激活
        """
        if len(self.indicator) < 1:
            return False
        
        current_value = self.indicator[0]
        
        if self.above:
            return current_value > self.threshold
        else:
            return current_value < self.threshold
