"""APIを呼ばずに会話ループとツール実行を確かめるテスト。"""

from types import SimpleNamespace as NS

import pytest

from jarvis.assistant import Assistant
from jarvis.config import Config
from jarvis.tools import ToolRegistry, registry


def cfg():
    return Config(model="claude-opus-5-5", effort="medium", user_name="")


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def text(t):
    return NS(type="text", text=t)


def tool_use(id_, name, input_):
    return NS(type="tool_use", id=id_, name=name, input=input_)


def resp(stop, *content):
    return NS(stop_reason=stop, content=list(content))


def test_plain_answer():
    client = FakeClient([resp("end_turn", text("こんにちは"))])
    a = Assistant(cfg(), confirm=lambda *_: True, client=client)
    assert a.ask("やあ") == "こんにちは"
    call = client.calls[0]
    assert call["fallbacks"] == "default"
    assert any(t.get("type") == "web_search_20260209" for t in call["tools"])


def test_tool_loop_runs_tool_and_returns_results_in_one_message():
    client = FakeClient(
        [
            resp(
                "tool_use",
                tool_use("t1", "get_current_time", {}),
                tool_use("t2", "get_system_info", {}),
            ),
            resp("end_turn", text("今は昼です")),
        ]
    )
    a = Assistant(cfg(), confirm=lambda *_: True, client=client)
    assert a.ask("今何時？") == "今は昼です"
    results = a.messages[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["t1", "t2"]
    assert not any(r["is_error"] for r in results)


def test_dangerous_tool_requires_confirmation():
    reg = ToolRegistry()
    ran = []

    @reg.tool("delete_thing", "テスト用", {"path": {"type": "string"}}, dangerous=True)
    def delete_thing(path):
        ran.append(path)
        return "deleted"

    denied = reg.run("delete_thing", {"path": "x"}, confirm=lambda *_: False)
    assert denied.is_error and ran == []
    ok = reg.run("delete_thing", {"path": "x"}, confirm=lambda *_: True)
    assert ok.content == "deleted" and ran == ["x"]


def test_unknown_tool_and_exception_become_errors():
    reg = ToolRegistry()

    @reg.tool("boom", "テスト用")
    def boom():
        raise RuntimeError("壊れた")

    assert reg.run("nope", {}, confirm=lambda *_: True).is_error
    r = reg.run("boom", {}, confirm=lambda *_: True)
    assert r.is_error and "壊れた" in r.content


def test_api_error_rolls_back_history():
    client = FakeClient(
        [resp("end_turn", text("1回目")), RuntimeError("network")]
    )
    a = Assistant(cfg(), confirm=lambda *_: True, client=client)
    a.ask("一つ目")
    with pytest.raises(RuntimeError):
        a.ask("二つ目")
    assert len(a.messages) == 2  # 失敗した発言は履歴に残らない


def test_refusal_and_pause_turn():
    client = FakeClient(
        [resp("pause_turn", text("")), resp("refusal")]
    )
    a = Assistant(cfg(), confirm=lambda *_: True, client=client)
    assert "お応えできません" in a.ask("?")
    assert len(client.calls) == 2


def test_tool_definitions_are_strict_schemas():
    for d in registry.api_definitions():
        assert d["strict"] is True
        assert d["input_schema"]["additionalProperties"] is False
