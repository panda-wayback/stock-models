def get_full_code(code: str) -> str:
    """
    将 6 位代码转换为 BaoStock 全称 (sh.xxxxxx, sz.xxxxxx, bj.xxxxxx)
    
    A股编码规则：
    - 60, 68, 90 -> 上海 (sh)
    - 00, 30, 20 -> 深圳 (sz)
    - 43, 83, 87 -> 北京 (bj)
    """
    # 如果已经是带点的格式(如 sz.000651)，直接返回
    if '.' in code:
        return code
    
    if code.startswith(('60', '68', '90')):  # 90 是沪市B股
        return f"sh.{code}"
    elif code.startswith(('00', '30', '20')): # 20 是深市B股
        return f"sz.{code}"
    elif code.startswith(('43', '83', '87')):
        return f"bj.{code}"
    else:
        # 默认兜底（或者报错）
        return f"sz.{code}"

