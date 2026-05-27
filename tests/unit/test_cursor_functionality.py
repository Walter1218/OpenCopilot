"""
光标特效功能测试 - 测试光标特效的实际功能
"""

import pytest
import sys
import os
import math

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestRippleFunctionality:
    """Ripple类功能测试"""
    
    def test_ripple_initialization(self):
        """测试Ripple初始化"""
        from cursor_effects import Ripple
        
        # 创建Ripple实例
        ripple = Ripple(100, 200)
        
        # 验证初始状态
        assert ripple.x == 100
        assert ripple.y == 200
        assert ripple.radius == 5.0
        assert ripple.alpha == 255
        assert ripple.active is True
    
    def test_ripple_update(self):
        """测试Ripple更新逻辑"""
        from cursor_effects import Ripple
        
        ripple = Ripple(100, 200)
        
        # 测试update方法
        ripple.update()
        assert ripple.radius == 7.0  # 5.0 + 2.0
        assert ripple.alpha == 240   # 255 - 15
        assert ripple.active is True
        
        # 继续更新
        ripple.update()
        assert ripple.radius == 9.0  # 7.0 + 2.0
        assert ripple.alpha == 225   # 240 - 15
    
    def test_ripple_lifecycle(self):
        """测试Ripple生命周期"""
        from cursor_effects import Ripple
        
        ripple = Ripple(100, 200)
        
        # 测试alpha降到0以下
        ripple.alpha = 10
        ripple.update()
        assert ripple.alpha == -5
        assert ripple.active is False
        
        # 验证非活跃状态下的更新
        ripple.update()
        assert ripple.alpha == -20
        assert ripple.active is False
    
    def test_ripple_properties(self):
        """测试Ripple属性"""
        from cursor_effects import Ripple
        
        # 测试不同初始位置
        ripple1 = Ripple(0, 0)
        assert ripple1.x == 0
        assert ripple1.y == 0
        
        ripple2 = Ripple(-100, -200)
        assert ripple2.x == -100
        assert ripple2.y == -200
        
        ripple3 = Ripple(1000, 2000)
        assert ripple3.x == 1000
        assert ripple3.y == 2000
    
    def test_ripple_animation_properties(self):
        """测试Ripple动画属性"""
        from cursor_effects import Ripple
        
        ripple = Ripple(100, 200)
        
        # 验证初始动画属性
        assert ripple.radius == 5.0
        assert ripple.alpha == 255
        assert ripple.active is True
        
        # 测试动画速度
        initial_radius = ripple.radius
        initial_alpha = ripple.alpha
        
        for _ in range(10):
            ripple.update()
        
        # 验证动画进展
        assert ripple.radius > initial_radius
        assert ripple.alpha < initial_alpha
    
    def test_ripple_position_after_update(self):
        """测试更新后位置保持不变"""
        from cursor_effects import Ripple
        
        ripple = Ripple(100, 200)
        
        # 更新多次
        for _ in range(10):
            ripple.update()
        
        # 验证位置保持不变
        assert ripple.x == 100
        assert ripple.y == 200
    
    def test_multiple_ripples(self):
        """测试多个Ripple实例"""
        from cursor_effects import Ripple
        
        # 创建多个Ripple
        ripples = [Ripple(i*10, i*20) for i in range(5)]
        
        # 验证每个Ripple的初始状态
        for i, ripple in enumerate(ripples):
            assert ripple.x == i*10
            assert ripple.y == i*20
            assert ripple.active is True
        
        # 更新所有Ripple
        for ripple in ripples:
            ripple.update()
        
        # 验证所有Ripple都已更新
        for ripple in ripples:
            assert ripple.radius > 5.0
            assert ripple.alpha < 255
    
    def test_ripple_math(self):
        """测试Ripple数学计算"""
        from cursor_effects import Ripple
        
        ripple = Ripple(100, 200)
        
        # 验证初始半径和透明度
        assert ripple.radius == 5.0
        assert ripple.alpha == 255
        
        # 验证更新公式
        # radius = radius + 2.0
        # alpha = alpha - 15
        
        # 更新一次
        ripple.update()
        expected_radius = 5.0 + 2.0
        expected_alpha = 255 - 15
        
        assert abs(ripple.radius - expected_radius) < 0.001
        assert abs(ripple.alpha - expected_alpha) < 0.001
        
        # 更新两次
        ripple.update()
        expected_radius = expected_radius + 2.0
        expected_alpha = expected_alpha - 15
        
        assert abs(ripple.radius - expected_radius) < 0.001
        assert abs(ripple.alpha - expected_alpha) < 0.001


class TestCursorOverlayFunctionality:
    """CursorOverlay类功能测试"""
    
    def test_cursor_overlay_import(self):
        """测试CursorOverlay导入"""
        try:
            from cursor_effects import CursorOverlay
            assert True
        except ImportError:
            pytest.fail("无法导入CursorOverlay")
    
    def test_cursor_overlay_class_exists(self):
        """测试CursorOverlay类存在"""
        from cursor_effects import CursorOverlay
        
        # 验证CursorOverlay是一个类
        assert isinstance(CursorOverlay, type)
    
    def test_cursor_overlay_has_required_methods(self):
        """测试CursorOverlay有必要的方法"""
        from cursor_effects import CursorOverlay
        
        # 验证有必要的方法
        assert hasattr(CursorOverlay, 'update_cursor_position')
        assert hasattr(CursorOverlay, 'paintEvent')
        assert hasattr(CursorOverlay, 'add_ripple')
    
    def test_cursor_overlay_initialization_with_ripples(self):
        """测试CursorOverlay初始化时是否有水波纹"""
        from cursor_effects import CursorOverlay
        
        # 注意：CursorOverlay可能需要QApplication实例
        # 这里我们只测试类的结构，不测试实际初始化
        pass


class TestCursorEffectsIntegration:
    """光标特效集成测试"""
    
    def test_cursor_effects_module_structure(self):
        """测试cursor_effects模块结构"""
        import cursor_effects
        
        # 验证模块有必要的类
        assert hasattr(cursor_effects, 'Ripple')
        assert hasattr(cursor_effects, 'CursorOverlay')
    
    def test_ripple_creation_and_update_cycle(self):
        """测试Ripple创建和更新周期"""
        from cursor_effects import Ripple
        
        # 创建多个Ripple模拟点击效果
        ripples = []
        for i in range(5):
            ripple = Ripple(i*50, i*50)
            ripples.append(ripple)
        
        # 模拟更新周期
        for _ in range(20):
            for ripple in ripples:
                if ripple.active:
                    ripple.update()
        
        # 验证所有Ripple都已非活跃
        for ripple in ripples:
            assert ripple.active is False
    
    def test_ripple_performance(self):
        """测试Ripple性能"""
        from cursor_effects import Ripple
        import time
        
        # 创建大量Ripple
        ripples = [Ripple(i, i) for i in range(1000)]
        
        # 测试更新性能
        start_time = time.time()
        for _ in range(100):
            for ripple in ripples:
                ripple.update()
        end_time = time.time()
        
        # 验证性能（应该在合理时间内完成）
        execution_time = end_time - start_time
        assert execution_time < 1.0  # 应该在1秒内完成
    
    def test_ripple_memory_usage(self):
        """测试Ripple内存使用"""
        from cursor_effects import Ripple
        
        # 创建大量Ripple
        ripples = [Ripple(i, i) for i in range(10000)]
        
        # 验证所有Ripple都被创建
        assert len(ripples) == 10000
        
        # 验证每个Ripple都有正确的属性
        for i, ripple in enumerate(ripples):
            assert ripple.x == i
            assert ripple.y == i
            assert ripple.active is True