"""
示例Python代码文件
用于测试代码解析功能
"""

import os
import sys
from typing import List, Dict, Any


class Calculator:
    """简单计算器类"""
    
    def __init__(self, name: str):
        self.name = name
        self.history: List[float] = []
    
    def add(self, a: float, b: float) -> float:
        """加法"""
        result = a + b
        self.history.append(result)
        return result
    
    def subtract(self, a: float, b: float) -> float:
        """减法"""
        result = a - b
        self.history.append(result)
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """乘法"""
        result = a * b
        self.history.append(result)
        return result
    
    def divide(self, a: float, b: float) -> float:
        """除法"""
        if b == 0:
            raise ValueError("除数不能为零")
        result = a / b
        self.history.append(result)
        return result
    
    def get_history(self) -> List[float]:
        """获取计算历史"""
        return self.history.copy()


def fibonacci(n: int) -> List[int]:
    """生成斐波那契数列"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib


def main():
    """主函数"""
    calc = Calculator("测试计算器")
    
    # 测试各种运算
    print(f"3 + 4 = {calc.add(3, 4)}")
    print(f"10 - 5 = {calc.subtract(10, 5)}")
    print(f"6 * 7 = {calc.multiply(6, 7)}")
    print(f"15 / 3 = {calc.divide(15, 3)}")
    
    # 测试斐波那契数列
    fib_sequence = fibonacci(10)
    print(f"斐波那契数列(前10项): {fib_sequence}")
    
    # 打印计算历史
    print(f"计算历史: {calc.get_history()}")


if __name__ == "__main__":
    main()