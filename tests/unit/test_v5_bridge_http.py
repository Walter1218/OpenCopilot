"""Bridge HTTP 调用成功路径测试

补充 bridge.py 中 get_active_document 的 HTTP 成功路径，
以及 get_browser_content 的 Safari 路径。

注意：bridge.py 中的 SystemProbeClient 和 httpx 是在函数内部延迟导入的，
因此需要在函数执行时通过 sys.modules 来 mock。
"""
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from unittest.mock import MagicMock, patch


# =============================================================================
# 1. get_active_document HTTP 成功路径
# =============================================================================

class TestGetActiveDocumentHTTPSuccess:
    """get_active_document HTTP 调用成功路径"""

    def test_http_success_returns_doc_info(self):
        """HTTP 200 应返回完整的文档信息"""
        mock_probe = MagicMock()
        mock_probe.get_frontmost_app.return_value = "VS Code"
        mock_probe.headers = {"X-Test": "1"}

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "file_path": "/project/main.py",
                "content": "def hello(): pass",
                "cursor_line": 42,
                "line_count": 100,
            }
        }

        mock_httpx = MagicMock()
        mock_httpx.get.return_value = mock_resp

        with patch.dict("sys.modules", {
            "system_probe_client": mock_probe_mod,
            "httpx": mock_httpx,
        }):
            from gui.v5.bridge import get_active_document
            result = get_active_document()

        assert result["status"] == "ok"
        assert result["app_name"] == "VS Code"
        assert result["file_path"] == "/project/main.py"
        assert result["content"] == "def hello(): pass"
        assert result["cursor_line"] == 42
        assert result["line_count"] == 100

    def test_http_success_with_empty_content(self):
        """HTTP 200 但内容为空"""
        mock_probe = MagicMock()
        mock_probe.get_frontmost_app.return_value = "VS Code"
        mock_probe.headers = {}

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {}}

        mock_httpx = MagicMock()
        mock_httpx.get.return_value = mock_resp

        with patch.dict("sys.modules", {
            "system_probe_client": mock_probe_mod,
            "httpx": mock_httpx,
        }):
            from gui.v5.bridge import get_active_document
            result = get_active_document()

        assert result["status"] == "ok"
        assert result["file_path"] == ""
        assert result["content"] == ""
        assert result["cursor_line"] == 0

    def test_http_404_returns_unavailable(self):
        """HTTP 404 应返回 unavailable 状态"""
        mock_probe = MagicMock()
        mock_probe.get_frontmost_app.return_value = "VS Code"
        mock_probe.headers = {}

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_httpx = MagicMock()
        mock_httpx.get.return_value = mock_resp

        with patch.dict("sys.modules", {
            "system_probe_client": mock_probe_mod,
            "httpx": mock_httpx,
        }):
            from gui.v5.bridge import get_active_document
            result = get_active_document()

        assert result["status"] == "unavailable"
        assert result["app_name"] == "VS Code"

    def test_http_timeout_falls_back(self):
        """HTTP 超时应有降级处理"""
        import httpx
        mock_probe = MagicMock()
        mock_probe.get_frontmost_app.return_value = "VS Code"
        mock_probe.headers = {}

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        mock_httpx = MagicMock()
        mock_httpx.get.side_effect = httpx.TimeoutException("timeout")

        with patch.dict("sys.modules", {
            "system_probe_client": mock_probe_mod,
            "httpx": mock_httpx,
        }):
            from gui.v5.bridge import get_active_document
            result = get_active_document()

        # 即使 HTTP 超时，也应返回基本信息
        assert result["app_name"] == "VS Code"
        assert "status" in result


# =============================================================================
# 2. get_browser_content Safari 路径
# =============================================================================

class TestGetBrowserContentSafari:
    """get_browser_content Safari 浏览器路径"""

    def test_safari_fallback_when_chrome_fails(self):
        """Chrome 不可用时回退到 Safari"""
        mock_probe = MagicMock()
        mock_probe.get_browser_dom.side_effect = [
            Exception("Chrome not available"),  # 第一次调用 Chrome 失败
            "Safari DOM content",               # 第二次调用 Safari 成功
        ]

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        with patch.dict("sys.modules", {"system_probe_client": mock_probe_mod}):
            from gui.v5.bridge import get_browser_content
            result = get_browser_content()

        assert result["status"] == "ok"
        assert result["browser"] == "Safari"
        assert result["text"] == "Safari DOM content"

    def test_safari_empty_content(self):
        """Safari 返回空内容"""
        mock_probe = MagicMock()
        mock_probe.get_browser_dom.side_effect = [
            Exception("Chrome not available"),
            "",  # Safari 返回空
        ]

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        with patch.dict("sys.modules", {"system_probe_client": mock_probe_mod}):
            from gui.v5.bridge import get_browser_content
            result = get_browser_content()

        assert result["status"] == "empty"
        assert result["browser"] == "Safari"

    def test_both_browsers_unavailable(self):
        """Chrome 和 Safari 都不可用"""
        mock_probe = MagicMock()
        mock_probe.get_browser_dom.side_effect = Exception("No browser")

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        with patch.dict("sys.modules", {"system_probe_client": mock_probe_mod}):
            from gui.v5.bridge import get_browser_content
            result = get_browser_content()

        assert result["status"] == "no_browser"
        assert result["text"] == ""


# =============================================================================
# 3. do_apply_to_ide broker 成功路径
# =============================================================================

class TestDoApplyToIDEBrokerSuccess:
    """do_apply_to_ide Broker 插入成功路径"""

    def test_broker_insert_success(self):
        """Broker 插入成功"""
        mock_probe = MagicMock()
        mock_probe.headers = {"X-Test": "1"}

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_httpx = MagicMock()
        mock_httpx.post.return_value = mock_resp

        with patch.dict("sys.modules", {
            "system_probe_client": mock_probe_mod,
            "httpx": mock_httpx,
        }):
            from gui.v5.bridge import do_apply_to_ide
            result = do_apply_to_ide("code to insert", action="insert")

        assert result["success"] is True
        assert result["method"] == "broker_insert"
        assert result["action"] == "insert"

    def test_broker_replace_success(self):
        """Broker replace 成功"""
        mock_probe = MagicMock()
        mock_probe.headers = {"X-Test": "1"}

        mock_probe_mod = MagicMock()
        mock_probe_mod.SystemProbeClient.return_value = mock_probe

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_httpx = MagicMock()
        mock_httpx.post.return_value = mock_resp

        with patch.dict("sys.modules", {
            "system_probe_client": mock_probe_mod,
            "httpx": mock_httpx,
        }):
            from gui.v5.bridge import do_apply_to_ide
            result = do_apply_to_ide("new code", action="replace")

        assert result["success"] is True
        assert result["action"] == "replace"
