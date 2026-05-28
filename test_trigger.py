import sys
from PyQt6.QtWidgets import QApplication
from smart_copilot import AICardWindow
from llm_provider import ProviderFactory

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

window = AICardWindow(ProviderFactory.create_provider())
window.context_source = "vision"
window.ai_card_image_base64 = "base64_data"
window.instruction_input.setText("hello")
window._on_custom_instruction()
print("Triggered successfully without TypeError.")
