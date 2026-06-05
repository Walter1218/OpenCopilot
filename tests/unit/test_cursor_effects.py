"""
Ripple 光标特效测试
"""
import pytest
import os



class TestRipple:
    """水波纹生命周期"""

    def test_init(self):
        from cursor_effects import Ripple
        r = Ripple(100, 200)
        assert r.x == 100
        assert r.y == 200
        assert r.radius == 5.0
        assert r.alpha == 255
        assert r.active is True

    def test_update(self):
        from cursor_effects import Ripple
        r = Ripple(100, 200)
        r.update()
        assert r.radius == 7.0
        assert r.alpha == 240
        assert r.active is True

    def test_lifecycle(self):
        from cursor_effects import Ripple
        r = Ripple(100, 200)
        r.alpha = 10
        r.update()
        assert r.alpha == -5
        assert r.active is False

    def test_full_lifecycle(self):
        from cursor_effects import Ripple
        r = Ripple(50, 50)
        for _ in range(20):
            if r.active:
                r.update()
        assert r.active is False

    def test_position_preserved(self):
        from cursor_effects import Ripple
        r = Ripple(100, 200)
        for _ in range(10):
            r.update()
        assert r.x == 100
        assert r.y == 200

    def test_multiple_ripples(self):
        from cursor_effects import Ripple
        ripples = [Ripple(i * 10, i * 20) for i in range(5)]
        for i, r in enumerate(ripples):
            assert r.x == i * 10
            assert r.y == i * 20
        for r in ripples:
            r.update()
        for r in ripples:
            assert r.radius > 5.0
            assert r.alpha < 255
