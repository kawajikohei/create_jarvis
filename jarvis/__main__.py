"""ターミナルで動くチャット版ジャービス。

    python -m jarvis
"""

from __future__ import annotations

import json
import sys

import anthropic

from .assistant import Assistant
from .config import Config

HELP = "コマンド: /reset 会話をリセット　/exit 終了"


def confirm(name: str, tool_input: dict) -> bool:
    print(f"\n⚠ ジャービスが「{name}」を実行しようとしています:")
    print(json.dumps(tool_input, ensure_ascii=False, indent=2))
    return input("実行してよいですか？ [y/N] ").strip().lower() in {"y", "yes", "はい"}


def show_tool(name: str, tool_input: dict) -> None:
    print(f"  … {name} を使用中", flush=True)


def main() -> int:
    # Windows のコンソールでも日本語が化けないようにする
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    try:
        cfg = Config.load()
        jarvis = Assistant(cfg, confirm=confirm, on_tool=show_tool)
    except (ValueError, anthropic.AnthropicError) as exc:
        print(f"起動できませんでした: {exc}")
        print(".env に ANTHROPIC_API_KEY が設定されているか確認してください。")
        return 1

    print(f"ジャービス起動（{cfg.model} / effort={cfg.effort}）。{HELP}")
    while True:
        try:
            text = input("\nあなた> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nまたいつでもどうぞ。")
            return 0
        if not text:
            continue
        if text in {"/exit", "/quit"}:
            print("またいつでもどうぞ。")
            return 0
        if text == "/reset":
            jarvis.reset()
            print("会話をリセットしました。")
            continue

        try:
            reply = jarvis.ask(text)
        except anthropic.AuthenticationError:
            print("APIキーが無効です。.env の ANTHROPIC_API_KEY を確認してください。")
            return 1
        except anthropic.RateLimitError:
            print("リクエストが混み合っています。少し待ってからもう一度どうぞ。")
            continue
        except anthropic.APIConnectionError:
            print("Claude に接続できませんでした。ネットワークを確認してください。")
            continue
        except anthropic.APIStatusError as exc:
            print(f"APIエラー ({exc.status_code}): {exc.message}")
            continue
        print(f"\nジャービス> {reply}")


if __name__ == "__main__":
    raise SystemExit(main())
