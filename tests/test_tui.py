import queue
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately

import tools
import tui as terminal_ui
from tui import (
    AgentEventHandler,
    TaskDisplay,
    _apply_event,
    _result_summary,
    _safe_text,
    compact_conversation_history,
)


class TerminalUiTests(unittest.TestCase):
    def test_registered_tools_have_display_metadata(self):
        names = {tool.name for tool in tools.get_tools()}
        metadata = tools.get_tool_metadata()
        self.assertEqual(names, set(metadata))
        self.assertTrue(all(item["category"] for item in metadata.values()))

    def test_callback_reports_tool_lifecycle_and_redacts_secrets(self):
        events = queue.Queue()
        handler = AgentEventHandler(
            events,
            {"sample_tool": {"category": "test tools", "description": "A test tool."}},
            first_tool_number=3,
        )
        run_id = UUID(int=1)
        handler.on_tool_start(
            {"name": "sample_tool"},
            '{"token": "should-not-appear"}',
            run_id=run_id,
            inputs={"token": "should-not-appear", "query": "hello"},
        )
        started = events.get_nowait()
        self.assertEqual(started.kind, "tool_started")
        execution = started.data["execution"]
        self.assertEqual(execution.number, 3)
        self.assertNotIn("should-not-appear", execution.arguments)
        self.assertIn("[REDACTED]", execution.arguments)
        self.assertIn("hello", execution.arguments)

        handler.on_tool_end("safe result", run_id=run_id)
        completed = events.get_nowait()
        self.assertEqual(completed.kind, "tool_completed")
        self.assertEqual(execution.status, "COMPLETED")
        self.assertGreaterEqual(execution.duration, 0)
        self.assertEqual(execution.result, "safe result")

    def test_sensitive_tool_output_is_not_shown(self):
        summary = _result_summary("read_file_content", "private document contents")
        self.assertNotIn("private document contents", summary)
        self.assertIn("hidden", summary)

    def test_callback_reports_tool_failures(self):
        events = queue.Queue()
        handler = AgentEventHandler(events, {}, first_tool_number=1)
        run_id = UUID(int=2)
        handler.on_tool_start(
            {"name": "sample_tool"},
            "{}",
            run_id=run_id,
            inputs={},
        )
        events.get_nowait()
        handler.on_tool_error(RuntimeError("tool failed"), run_id=run_id)
        failed = events.get_nowait()
        self.assertEqual(failed.kind, "tool_failed")
        self.assertEqual(failed.data["execution"].status, "FAILED")
        self.assertIn("tool failed", failed.data["execution"].result)

    def test_task_state_uses_final_agent_response(self):
        task = TaskDisplay(prompt="test")
        response = {"messages": [SimpleNamespace(content="Actual result")]}
        _apply_event(
            task,
            SimpleNamespace(
                kind="task_completed",
                message="Task completed.",
                data={"response": response},
            ),
        )
        self.assertEqual(task.status, "COMPLETED")
        self.assertEqual(task.result, "Actual result")

    def test_safe_text_redacts_credentials_and_terminal_controls(self):
        safe = _safe_text("api_key=secret-value\x1b[31mred\x1b[0m")
        self.assertNotIn("secret-value", safe)
        self.assertNotIn("\x1b", safe)
        self.assertIn("[REDACTED]", safe)

    def test_history_compaction_removes_tool_transcripts_and_keeps_final_answer(self):
        messages = [
            HumanMessage(content="Check the weather."),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_weather",
                        "args": {"city": "London"},
                        "id": "call-weather",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                content="large weather payload that should not be replayed",
                tool_call_id="call-weather",
            ),
            AIMessage(content="It is currently 12 degrees."),
            HumanMessage(content="Is that cold?"),
            AIMessage(content="It is cool; consider a light jacket."),
        ]

        compacted = compact_conversation_history(messages, max_tokens=500)

        self.assertEqual([message.type for message in compacted], ["human", "ai", "human", "ai"])
        self.assertNotIn(
            "large weather payload that should not be replayed",
            [message.content for message in compacted],
        )
        self.assertEqual(compacted[-1].content, "It is cool; consider a light jacket.")

    def test_history_is_limited_by_recent_turn_count_and_token_budget(self):
        messages = []
        for index in range(8):
            messages.extend(
                [
                    HumanMessage(content=f"question {index} " + "extra words " * 20),
                    AIMessage(content=f"answer {index} " + "more words " * 20),
                ]
            )

        compacted = compact_conversation_history(messages, max_tokens=150, max_turns=2)

        self.assertEqual(len(compacted), 2)
        self.assertTrue(compacted[0].content.startswith("question 7"))
        self.assertEqual(compacted[-1].content.split()[1], "7")
        self.assertLessEqual(count_tokens_approximately(compacted), 150)

    def test_plain_terminal_fallback_runs_agent_without_rich(self):
        class FakeAgent:
            def __init__(self):
                self.calls = 0

            def invoke(self, state, config):
                self.calls += 1
                self.assert_callbacks = config["callbacks"]
                return {
                    "messages": state["messages"]
                    + [SimpleNamespace(content="Fallback response")]
                }

        fake_agent = FakeAgent()
        with patch.object(terminal_ui, "HAS_RICH", False), patch(
            "builtins.input", side_effect=["hello", "/quit"]
        ), patch("builtins.print"):
            terminal_ui.run_terminal_chat(fake_agent, [], {}, "test-model")
        self.assertEqual(fake_agent.calls, 1)
        self.assertEqual(len(fake_agent.assert_callbacks), 1)


if __name__ == "__main__":
    unittest.main()
