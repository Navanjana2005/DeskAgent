import unittest

from langchain_core.messages import AIMessage, HumanMessage

from openrouter import OpenRouterChatOpenAI
from tui import compact_conversation_history


class OpenRouterAdapterTests(unittest.TestCase):
    def setUp(self):
        self.model = OpenRouterChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            api_key="offline-test-placeholder",
            extra_body={"reasoning": {"enabled": True}},
        )

    def test_response_reasoning_details_are_preserved(self):
        details = [{"type": "reasoning.text", "text": "provider metadata"}]
        result = self.model._create_chat_result(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Answer",
                            "reasoning_details": details,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            }
        )

        message = result.generations[0].message
        self.assertIsInstance(message, AIMessage)
        self.assertEqual(message.additional_kwargs["reasoning_details"], details)

    def test_reasoning_details_are_replayed_in_follow_up_payload(self):
        details = [{"type": "reasoning.text", "text": "opaque provider value"}]
        assistant = AIMessage(
            content="Answer",
            additional_kwargs={"reasoning_details": details},
        )

        payload = self.model._get_request_payload(
            [
                HumanMessage(content="Question"),
                assistant,
                HumanMessage(content="Follow-up"),
            ]
        )

        self.assertIs(payload["messages"][1]["reasoning_details"], details)
        self.assertEqual(payload["messages"][1]["content"], "Answer")

    def test_history_compaction_keeps_reasoning_details_for_replay(self):
        details = [{"type": "reasoning.text", "text": "provider value"}]
        history = compact_conversation_history(
            [
                HumanMessage(content="Question"),
                AIMessage(
                    content="Answer",
                    additional_kwargs={"reasoning_details": details},
                ),
            ],
            max_tokens=200,
        )

        payload = self.model._get_request_payload(history)

        self.assertIs(payload["messages"][1]["reasoning_details"], details)


if __name__ == "__main__":
    unittest.main()
