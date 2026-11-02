"""ツール（Claudeが呼び出せる機能）を登録・実行する仕組み。

新しい機能を足すときは、関数に @registry.tool(...) を付けるだけで
Claude に自動で公開されます。危険な操作は dangerous=True にすると、
実行前に必ずユーザーへ確認を取ります。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

ConfirmFn = Callable[[str, dict[str, Any]], bool]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Callable[..., Any]
    dangerous: bool = False

    def to_api(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "strict": True,
        }


@dataclass
class ToolResult:
    content: str
    is_error: bool = False


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def tool(
        self,
        name: str,
        description: str,
        properties: dict[str, Any] | None = None,
        required: list[str] | None = None,
        dangerous: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """関数をツールとして登録するデコレーター。"""

        properties = properties or {}
        schema = {
            "type": "object",
            "properties": properties,
            # strict モードでは全プロパティを required にする必要がある
            "required": required if required is not None else list(properties),
            "additionalProperties": False,
        }

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if name in self.tools:
                raise ValueError(f"ツール名が重複しています: {name}")
            self.tools[name] = Tool(name, description, schema, func, dangerous)
            return func

        return decorator

    def api_definitions(self) -> list[dict[str, Any]]:
        return [t.to_api() for t in self.tools.values()]

    def run(self, name: str, tool_input: Any, confirm: ConfirmFn) -> ToolResult:
        tool = self.tools.get(name)
        if tool is None:
            return ToolResult(f"不明なツールです: {name}", is_error=True)
        if not isinstance(tool_input, dict):
            return ToolResult("ツールの入力が不正です（オブジェクトではありません）", is_error=True)

        if tool.dangerous and not confirm(name, tool_input):
            return ToolResult("ユーザーが実行を拒否しました。別の方法を提案してください。", is_error=True)

        try:
            result = tool.func(**tool_input)
        except Exception as exc:  # ツール内の失敗はClaudeに伝えて立て直させる
            return ToolResult(f"{type(exc).__name__}: {exc}", is_error=True)

        if isinstance(result, str):
            return ToolResult(result)
        return ToolResult(json.dumps(result, ensure_ascii=False, default=str))


registry = ToolRegistry()
