"""
自定义手续费和印花税计算
"""
import backtrader as bt


class ChinaStockCommInfo(bt.CommInfoBase):
    """
    中国A股手续费和印花税计算
    
    规则：
    1. 手续费：买入和卖出都收取（默认 0.03%）
    2. 印花税：仅卖出时收取（默认 0.1%）
    3. 最小手续费：5元
    """
    
    params = (
        ('commission', 0.0003),      # 手续费率 0.03%
        ('stamp_tax', 0.001),         # 印花税率 0.1%
        ('min_commission', 5.0),      # 最小手续费 5元
        ('stocklike', True),          # 股票模式
        ('commtype', bt.CommInfoBase.COMM_PERC),  # 按百分比
        ('percabs', True),            # commission 是绝对小数（不是百分比）
    )
    
    def _getcommission(self, size, price, pseudoexec):
        """
        计算总费用（手续费 + 印花税）
        
        参数:
        - size: 交易数量（正数=买入，负数=卖出）
        - price: 价格
        - pseudoexec: 是否为模拟执行
        
        返回:
        总费用（手续费 + 印花税）
        """
        value = abs(size) * price
        
        # 计算手续费
        commission = value * self.p.commission
        
        # 应用最小手续费（手续费不能小于最小值）
        if commission < self.p.min_commission:
            commission = self.p.min_commission
        
        # 印花税（仅卖出时收取）
        stamp_tax = 0.0
        if size < 0:  # 卖出
            stamp_tax = value * self.p.stamp_tax
        
        # 返回总费用
        total_cost = commission + stamp_tax
        
        # 调试信息（可选，生产环境可关闭）
        # if not pseudoexec:
        #     print(f"费用计算: size={size}, price={price:.2f}, value={value:.2f}, "
        #           f"commission={commission:.2f}, stamp_tax={stamp_tax:.2f}, total={total_cost:.2f}")
        
        return total_cost
