import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
import sys
import os

# Add root dir to sys path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Ensure QApplication exists for tests
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from smart_copilot import AICardWindow
import httpx

class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data
        
    def json(self):
        return self._json_data

@patch("smart_copilot.httpx.get")
@patch.object(AICardWindow, "_get_ide_port", return_value="12345")
def test_ide_advanced_context(mock_get_port, mock_get):
    
    # Mock different endpoint responses
    def side_effect(url, **kwargs):
        if url.endswith("/selection"):
            return MockResponse(200, {"text": "", "range": None})
        elif url.endswith("/diagnostics"):
            return MockResponse(200, {
                "diagnostics": [
                    {"severity": 0, "message": "TypeError: something is wrong", "line": 42}
                ]
            })
        elif url.endswith("/git-diff"):
            return MockResponse(200, {"diff": "- old line\n+ new line"})
        elif url.endswith("/symbol"):
            return MockResponse(200, {
                "name": "my_function",
                "text": "def my_function():\n    pass",
                "range": {"startLine": 10, "endLine": 12}
            })
        elif url.endswith("/context"):
            return MockResponse(200, {
                "content": "def my_function():\n    pass\n\n# more code...",
                "fileName": "test.py",
                "languageId": "python"
            })
        return MockResponse(404, {})

    mock_get.side_effect = side_effect
    
    # Mock Provider
    mock_provider = MagicMock()
    
    # Call the method
    window = AICardWindow(provider=mock_provider)
    window.read_from_ide_extension()
    
    # Verify the results
    assert window.context_source == "ide"
    assert window.current_text == "def my_function():\n    pass" # Should pick symbol text
    assert window.context_meta["file_name"] == "test.py"
    assert len(window.context_meta["diagnostics"]) == 1
    assert window.context_meta["diagnostics"][0]["message"] == "TypeError: something is wrong"
    assert window.context_meta["git_diff"] == "- old line\n+ new line"
    assert window.context_meta["symbol"]["name"] == "my_function"
    
    # Check UI output
    text = window.text_edit.toPlainText()
    assert "发现 1 个诊断报错 🎯" in text
    assert "智能截取光标所在代码块 [my_function]" in text
