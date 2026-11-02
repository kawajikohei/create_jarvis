"""Claude とツールをつなぐ会話エンジン（ジャービスの頭脳部分）。"""

from __future__ import annotations

from typing import Any, Callable

import anthropic

from .config import Config
from .tools import ToolRegistry, registry as default_registry
from .tools.registry import ConfirmFn

# Anthropic 側で実行されるWeb検索ツール（調べ物用）
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}

# 安全分類器で断られた場合、サーバー側で自動的に別モデルへ切り替える
FALLBACK_BETA = "server-side-fallback-2026-07-01"

MAX_STEPS = 25  # 1回の依頼でツールを呼び合う最大回数（暴走防止）


def build_system_prompt(cfg: Config) -> str:
    who = f"ユーザーの名前は{cfg.user_name}です。" if cfg.user_name else ""
    return (
        "あなたは「ジャービス」、Windows PC 上で動くユーザー専用のAIアシスタントです。"
        f"{who}"
        "日本語で、簡潔かつ丁寧に答えてください。"
        "ツールで確かめられることは推測せずツールを使い、最新情報が必要なときは web_search で調べて出典を示してください。"
        "ファイルの削除や上書きなど取り返しのつかない操作は、ツール側で確認が入るので、目的をはっきり伝えてから呼び出してください。"
    )


class Assistant:
    def __init__(
        self,
        cfg: Config,
        confirm: ConfirmFn,
        tools: ToolRegistry = default_registry,
        client: anthropic.Anthropic | None = None,
        on_tool: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.cfg = cfg
        self.confirm = confirm
        self.tools = tools
        self.client = client or anthropic.Anthropic()
        self.on_tool = on_tool
        self.messages: list[dict[str, Any]] = []
        self.system = build_system_prompt(cfg)

    def reset(self) -> None:
        self.messages = []

    def _request(self):
        return self.client.beta.messages.create(
            model=self.cfg.model,
            max_tokens=self.cfg.max_tokens,
            system=self.system,
            messages=self.messages,
            tools=[*self.tools.api_definitions(), WEB_SEARCH_TOOL],
            thinking={"type": "adaptive"},
            output_config={"effort": self.cfg.effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )

    def ask(self, user_text: str) -> str:
        """ユーザーの発言を受け取り、必要ならツールを使って最終的な返答を返す。

        API エラーが起きたときは、この発言の分だけ履歴を巻き戻してから例外を投げ直す。
        """
        checkpoint = len(self.messages)
        try:
            return self._ask(user_text)
        except Exception:
            del self.messages[checkpoint:]
            raise

    def _ask(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_STEPS):
            response = self._request()
            # thinking ブロックなども含めて丸ごと履歴に残す（そのまま返す必要がある）
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return "申し訳ありません、その依頼にはお応えできませんでした。"

            if response.stop_reason == "pause_turn":
                continue  # サーバー側ツール（Web検索）の途中。続きを依頼する

            if response.stop_reason == "tool_use":
                results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    if self.on_tool:
                        self.on_tool(block.name, block.input)
                    result = self.tools.run(block.name, block.input, self.confirm)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.content,
                            "is_error": result.is_error,
                        }
                    )
                # 並列ツール呼び出しの結果は1つのメッセージにまとめて返す
                self.messages.append({"role": "user", "content": results})
                continue

            text = _text_of(response.content)
            if response.stop_reason == "max_tokens":
                text += "\n（返答が長すぎて途中で切れました）"
            return text or "（返答が空でした）"

        return "ツールの呼び出しが多すぎたため中断しました。依頼を分けてもう一度お願いします。"


def _text_of(content: list[Any]) -> str:
    return "".join(b.text for b in content if getattr(b, "type", None) == "text").strip()
