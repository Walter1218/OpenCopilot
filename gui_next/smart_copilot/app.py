from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .services import UnifiedApiClient
from .shell import FloatingPanel


def run_headless_flow(
    api_base_url: str,
    *,
    client: Any | None = None,
    source_app: str = "Cursor",
    document_title: str = "demo.py",
    selection_text: str = "def legacy_func(x):\n    return x",
    action: str = "review",
    user_input: str = "请帮我 review 并输出更好的版本",
) -> dict[str, Any]:
    api_client = UnifiedApiClient(base_url=api_base_url, client=client)
    panel = FloatingPanel(api_client=api_client)
    try:
        panel.summon(
            source_app=source_app,
            selection_text=selection_text,
            document_title=document_title,
            metadata={"interactive_test": True, "headless": True},
        )
        panel.run_action(action=action, user_input=user_input, max_polls=20, interval_sec=0.25)
        if panel.task_vm.apply_bar.can_preview:
            panel.preview_latest_apply()
            if panel.task_vm.apply_bar.can_commit:
                panel.commit_latest_preview()
        return panel.snapshot()
    finally:
        panel.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smart Copilot vNext interactive test app")
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="Unified API base URL, default: http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a headless flow and print the resulting state as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    api_base_url = args.api_base_url.rstrip("/")

    if args.smoke_test:
        snapshot = run_headless_flow(api_base_url)
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return 0

    from PyQt6.QtWidgets import QApplication

    from .shell.interactive_window import InteractiveTestWindow

    app = QApplication(sys.argv)
    window = InteractiveTestWindow(api_base_url=api_base_url)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
