import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[1] / "test codes" / "test_llm_api.py"
SPEC = importlib.util.spec_from_file_location("test_llm_api_script", SCRIPT_PATH)
API_TEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API_TEST)


class FakeMessage:
    def __init__(self, content, reasoning_details=None):
        self.content = content
        self.reasoning_details = reasoning_details


class FakeOpenAIClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        self.responses = [
            FakeMessage("First answer", [{"type": "opaque", "value": "same object"}]),
            FakeMessage("Second answer"),
        ]
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = self.responses[len(self.calls) - 1]
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class OpenRouterApiScriptTests(unittest.TestCase):
    def test_test_script_replays_reasoning_details_in_second_request(self):
        fake_client = FakeOpenAIClient()
        with (
            patch.dict(
                os.environ,
                {
                    "OPENROUTER_API_KEY": "offline-placeholder",
                    "OPENROUTER_TIMEOUT_SECONDS": "180",
                    "OPENROUTER_MODEL": "test/model",
                },
                clear=True,
            ),
            patch.object(API_TEST, "OpenAI", return_value=fake_client),
            patch.object(API_TEST.dotenv, "load_dotenv"),
            patch.object(sys, "argv", [str(SCRIPT_PATH)]),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = API_TEST.main()

        self.assertEqual(result, 0)
        self.assertEqual(len(fake_client.calls), 2)
        first_reasoning = fake_client.responses[0].reasoning_details
        self.assertIs(
            fake_client.calls[1]["messages"][1]["reasoning_details"],
            first_reasoning,
        )
        self.assertEqual(
            fake_client.calls[0]["extra_body"],
            {"reasoning": {"enabled": True}},
        )

    def test_test_script_uses_requested_nvidia_endpoint_and_parameters(self):
        fake_client = FakeOpenAIClient()

        def fake_openai_factory(**kwargs):
            fake_client.kwargs = kwargs
            return fake_client

        with (
            patch.dict(
                os.environ,
                {
                    "NVIDIA_API_KEY": "offline-placeholder",
                    "NVIDIA_TIMEOUT_SECONDS": "90",
                    "NVIDIA_MODEL": "z-ai/glm-5.3-flash",
                },
                clear=True,
            ),
            patch.object(API_TEST, "OpenAI", side_effect=fake_openai_factory),
            patch.object(API_TEST.dotenv, "load_dotenv"),
            patch.object(
                sys,
                "argv",
                [str(SCRIPT_PATH), "--provider", "nvidia"],
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = API_TEST.main()

        self.assertEqual(result, 0)
        self.assertEqual(
            fake_client.kwargs["base_url"],
            "https://integrate.api.nvidia.com/v1",
        )
        self.assertEqual(fake_client.kwargs["timeout"], 90)
        call = fake_client.calls[0]
        self.assertEqual(call["model"], "z-ai/glm-5.3-flash")
        self.assertEqual(call["temperature"], 0.5)
        self.assertEqual(call["top_p"], 1)
        self.assertEqual(call["max_tokens"], 1024)
        self.assertFalse(call["stream"])


if __name__ == "__main__":
    unittest.main()
