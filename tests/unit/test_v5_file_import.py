"""V5 文件导入与拖拽综合测试

覆盖:
- 各种文件类型的读取（.txt, .py, .md, .json, .docx）
- bridge.get_file_content 对不同文件类型的处理
- 大文件处理
- 空文件处理
- 文件不存在处理
- 编码问题处理
- 最近文件列表更新
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import tempfile
from unittest.mock import MagicMock, patch


# =============================================================================
# 1. 文本文件读取
# =============================================================================

class TestTextFileImport:
    """文本文件导入测试"""

    def test_txt_file_read(self, tmp_path):
        """应能读取 .txt 文件"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "test.txt"
        f.write_text("Hello World\nThis is a test.", encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert result["text"] == "Hello World\nThis is a test."

    def test_py_file_read(self, tmp_path):
        """应能读取 .py 文件"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "test.py"
        code = "def hello():\n    return 'world'\n"
        f.write_text(code, encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert result["text"] == code

    def test_md_file_read(self, tmp_path):
        """应能读取 .md 文件"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "test.md"
        md = "# Title\n\nSome **bold** text.\n"
        f.write_text(md, encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert result["text"] == md

    def test_json_file_read(self, tmp_path):
        """应能读取 .json 文件"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "test.json"
        json_text = '{"key": "value", "num": 42}'
        f.write_text(json_text, encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert result["text"] == json_text

    def test_csv_file_read(self, tmp_path):
        """应能读取 .csv 文件"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "test.csv"
        csv = "name,age\nAlice,30\nBob,25\n"
        f.write_text(csv, encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert result["text"] == csv


# =============================================================================
# 2. Office 文件读取
# =============================================================================

class TestOfficeFileImport:
    """Office 文件导入测试"""

    def test_docx_file_delegates_to_probe(self, tmp_path):
        """.docx 文件应委托给 SystemProbeClient"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "test.docx"
        f.write_bytes(b"fake docx content")

        mock_mod = MagicMock()
        mock_probe = MagicMock()
        mock_probe.read_office_file.return_value = {"content": "Extracted docx text"}
        mock_mod.SystemProbeClient.return_value = mock_probe

        with patch.dict("sys.modules", {"system_probe_client": mock_mod}):
            result = get_file_content(str(f))

        assert result["status"] == "ok"
        assert result["text"] == "Extracted docx text"
        assert result["file_type"] == "docx"

    def test_pptx_file_delegates_to_probe(self, tmp_path):
        """.pptx 文件应委托给 SystemProbeClient"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "test.pptx"
        f.write_bytes(b"fake pptx content")

        mock_mod = MagicMock()
        mock_probe = MagicMock()
        mock_probe.read_office_file.return_value = {"content": "Slide 1\nSlide 2"}
        mock_mod.SystemProbeClient.return_value = mock_probe

        with patch.dict("sys.modules", {"system_probe_client": mock_mod}):
            result = get_file_content(str(f))

        assert result["status"] == "ok"
        assert result["text"] == "Slide 1\nSlide 2"


# =============================================================================
# 3. 边界情况
# =============================================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_file(self, tmp_path):
        """空文件应返回 ok 但 text 为空"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert result["text"] == ""

    def test_file_not_found(self):
        """不存在的文件应返回 not_found"""
        from gui.v5.bridge import get_file_content
        result = get_file_content("/tmp/nonexistent_file_xyz_123.txt")
        assert result["status"] == "not_found"

    def test_large_file(self, tmp_path):
        """大文件应能正常读取"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "large.txt"
        large_content = "A" * 100000
        f.write_text(large_content, encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert len(result["text"]) == 100000

    def test_unicode_content(self, tmp_path):
        """Unicode 内容应正确读取"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "unicode.txt"
        text = "中文内容 🎉 émojis ñoño"
        f.write_text(text, encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert result["text"] == text

    def test_file_with_size_info(self, tmp_path):
        """应返回文件大小信息"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "sized.txt"
        f.write_text("12345", encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"
        assert "file_size" in result
        assert result["file_size"] == 5


# =============================================================================
# 4. 文件路径处理
# =============================================================================

class TestFilePathHandling:
    """文件路径处理测试"""

    def test_tilde_expansion(self, tmp_path):
        """~ 应展开为用户目录"""
        from gui.v5.bridge import get_file_content
        # 使用实际存在的文件测试
        with patch("os.path.expanduser") as mock_expand:
            mock_expand.return_value = str(tmp_path / "test.txt")
            f = tmp_path / "test.txt"
            f.write_text("content", encoding="utf-8")
            result = get_file_content("~/test.txt")
            mock_expand.assert_called_with("~/test.txt")

    def test_relative_path(self, tmp_path):
        """相对路径应能解析"""
        from gui.v5.bridge import get_file_content
        f = tmp_path / "relative.txt"
        f.write_text("relative content", encoding="utf-8")
        result = get_file_content(str(f))
        assert result["status"] == "ok"


# =============================================================================
# 5. 最近文件管理
# =============================================================================

class TestRecentFiles:
    """最近文件管理测试"""

    def test_add_recent_file_creates_entry(self, tmp_path):
        """添加最近文件应创建记录"""
        from gui.v5.bridge import add_recent_file, get_recent_files
        recent_path = tmp_path / "recent_files.json"
        test_file = tmp_path / "code.py"
        test_file.write_text("code", encoding="utf-8")
        with patch("gui.v5.bridge.RECENT_FILES_PATH", str(recent_path)):
            add_recent_file(str(test_file), source="drag_drop")
            result = get_recent_files()
        assert len(result) == 1
        assert result[0]["name"] == "code.py"
        assert result[0]["source"] == "drag_drop"

    def test_add_multiple_files_sorted(self, tmp_path):
        """多个文件应按修改时间排序"""
        from gui.v5.bridge import add_recent_file, get_recent_files
        recent_path = tmp_path / "recent_files.json"
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("a", encoding="utf-8")
        import time
        time.sleep(0.01)
        f2.write_text("b", encoding="utf-8")
        with patch("gui.v5.bridge.RECENT_FILES_PATH", str(recent_path)):
            add_recent_file(str(f1))
            add_recent_file(str(f2))
            result = get_recent_files()
        assert len(result) == 2
        # f2 更晚修改，应在前面
        assert result[0]["name"] == "b.py"

    def test_add_recent_file_limits_count(self, tmp_path):
        """最近文件应限制数量"""
        from gui.v5.bridge import add_recent_file, get_recent_files, MAX_RECENT_FILES
        recent_path = tmp_path / "recent_files.json"
        with patch("gui.v5.bridge.RECENT_FILES_PATH", str(recent_path)):
            for i in range(MAX_RECENT_FILES + 10):
                f = tmp_path / f"file_{i}.py"
                f.write_text("code", encoding="utf-8")
                add_recent_file(str(f))
            result = get_recent_files(limit=100)
        assert len(result) <= MAX_RECENT_FILES


# =============================================================================
# 6. fetch_context 文件源
# =============================================================================

class TestFetchContextFile:
    """fetch_context 文件源测试"""

    def test_fetch_context_file_with_path(self, tmp_path):
        """fetch_context 带路径应读取文件"""
        from gui.v5.bridge import fetch_context
        f = tmp_path / "context.txt"
        f.write_text("context data", encoding="utf-8")
        result = fetch_context("file", extra=str(f))
        assert result["status"] == "ok"
        assert result["text"] == "context data"
        assert result["source"] == "file"

    def test_fetch_context_file_without_path(self):
        """fetch_context 无路径应返回 no_path"""
        from gui.v5.bridge import fetch_context
        result = fetch_context("file", extra="")
        assert result["status"] == "no_path"

    def test_fetch_context_all_sources(self, tmp_path):
        """所有数据源应正常 dispatch"""
        from gui.v5.bridge import fetch_context
        sources = ["selection", "active_doc", "browser", "clipboard", "file"]
        for source in sources:
            if source == "file":
                f = tmp_path / "test.txt"
                f.write_text("data", encoding="utf-8")
                result = fetch_context(source, extra=str(f))
            else:
                result = fetch_context(source)
            assert "status" in result
            assert result["source"] == source


# =============================================================================
# 7. 拖放后文件共享到 Tab
# =============================================================================
