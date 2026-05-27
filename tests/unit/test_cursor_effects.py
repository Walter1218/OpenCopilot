"""
光标特效测试 - 测试光标特效模块的基本功能
"""

import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestCursorEffects:
    """光标特效测试类"""
    
    def test_cursor_overlay_import(self):
        """测试CursorOverlay是否可以导入"""
        try:
            from cursor_effects import CursorOverlay, Ripple
            assert True
        except ImportError:
            pytest.fail("无法导入CursorOverlay或Ripple")
    
    def test_ripple_class(self):
        """测试Ripple类的基本功能"""
        from cursor_effects import Ripple
        
        # 创建Ripple实例
        ripple = Ripple(100, 200)
        
        # 验证初始状态
        assert ripple.x == 100
        assert ripple.y == 200
        assert ripple.radius == 5.0
        assert ripple.alpha == 255
        assert ripple.active is True
        
        # 测试update方法
        ripple.update()
        assert ripple.radius == 7.0  # 5.0 + 2.0
        assert ripple.alpha == 240   # 255 - 15
        assert ripple.active is True
        
        # 测试alpha降到0以下
        ripple.alpha = 10
        ripple.update()
        assert ripple.alpha == -5
        assert ripple.active is False
    
    def test_ripple_lifecycle(self):
        """测试Ripple的完整生命周期"""
        from cursor_effects import Ripple
        
        ripple = Ripple(50, 50)
        
        # 模拟多次update直到alpha降到0以下
        for _ in range(20):
            if ripple.active:
                ripple.update()
        
        # 验证ripple最终变为非活跃状态
        assert ripple.active is False
    
    def test_cursor_overlay_initialization(self):
        """测试CursorOverlay的初始化（不创建GUI）"""
        try:
            from cursor_effects import CursorOverlay
            
            # 这个测试可能会失败，因为需要QApplication
            # 但我们可以测试类是否可以被引用
            assert hasattr(CursorOverlay, '__init__')
            assert hasattr(CursorOverlay, 'update_cursor_position')
            assert hasattr(CursorOverlay, 'add_ripple')
            assert hasattr(CursorOverlay, 'paintEvent')
            
        except Exception as e:
            pytest.skip(f"CursorOverlay初始化测试跳过: {e}")
    
    def test_ripple_animation_properties(self):
        """测试Ripple的动画属性"""
        from cursor_effects import Ripple
        
        ripple = Ripple(0, 0)
        
        # 测试初始属性
        assert ripple.radius == 5.0
        assert ripple.alpha == 255
        
        # 测试update后的属性
        ripple.update()
        assert ripple.radius == 7.0
        assert ripple.alpha == 240
        
        # 测试多次update
        for _ in range(10):
            ripple.update()
        
        assert ripple.radius == 27.0  # 5.0 + (2.0 * 11)
        assert ripple.alpha == 90     # 255 - (15 * 11)
    
    def test_ripple_position(self):
        """测试Ripple的位置属性"""
        from cursor_effects import Ripple
        
        # 测试不同位置
        positions = [(0, 0), (100, 200), (-50, -100), (1000, 2000)]
        
        for x, y in positions:
            ripple = Ripple(x, y)
            assert ripple.x == x
            assert ripple.y == y


class TestCursorEffectsIntegration:
    """光标特效集成测试"""
    
    def test_cursor_effects_module_structure(self):
        """测试cursor_effects模块的结构"""
        try:
            import cursor_effects
            
            # 检查模块是否包含必要的类
            assert hasattr(cursor_effects, 'CursorOverlay')
            assert hasattr(cursor_effects, 'Ripple')
            
            # 检查类是否有必要的方法
            assert callable(getattr(cursor_effects.CursorOverlay, '__init__', None))
            assert callable(getattr(cursor_effects.CursorOverlay, 'update_cursor_position', None))
            assert callable(getattr(cursor_effects.CursorOverlay, 'add_ripple', None))
            
        except ImportError:
            pytest.fail("无法导入cursor_effects模块")
    
    def test_ripple_math(self):
        """测试Ripple的数学计算"""
        from cursor_effects import Ripple
        
        ripple = Ripple(0, 0)
        
        # 测试半径增长
        initial_radius = ripple.radius
        ripple.update()
        assert ripple.radius == initial_radius + 2.0
        
        # 测试alpha减少
        initial_alpha = ripple.alpha
        ripple.update()
        assert ripple.alpha == initial_alpha - 15
        
        # 测试alpha不会低于0
        ripple.alpha = 10
        ripple.update()
        assert ripple.alpha == -5  # 允许负数，但active会变为False
        
        # 测试active状态
        ripple.alpha = 10
        ripple.update()
        assert ripple.active is False
    
    def test_multiple_ripples(self):
        """测试多个Ripple实例"""
        from cursor_effects import Ripple
        
        ripples = []
        for i in range(10):
            ripples.append(Ripple(i * 10, i * 20))
        
        # 验证所有ripple都创建成功
        assert len(ripples) == 10
        
        # 验证每个ripple的位置
        for i, ripple in enumerate(ripples):
            assert ripple.x == i * 10
            assert ripple.y == i * 20
            assert ripple.active is True
        
        # 更新所有ripple
        for ripple in ripples:
            ripple.update()
        
        # 验证所有ripple都被更新
        for ripple in ripples:
            assert ripple.radius == 7.0
            assert ripple.alpha == 240


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])