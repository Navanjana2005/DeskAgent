import unittest
from unittest.mock import patch

from langchain_core.runnables import RunnableBinding

from openrouter import OpenRouterChatOpenAI
from providers import (
    PROVIDERS,
    NvidiaChatOpenAI,
    build_chat_model,
    configured_model_name,
    select_provider,
)


class ProviderSelectionTests(unittest.TestCase):
    def test_select_provider_retries_invalid_choice(self):
        prompts = iter(["3", "2"])
        messages = []

        def fake_input(prompt):
            messages.append(prompt)
            return next(prompts)

        provider = select_provider(
            input_fn=fake_input,
            output_fn=messages.append,
        )
        self.assertEqual(provider.key, "nvidia")
        self.assertTrue(any("Invalid selection" in message for message in messages))

    def test_nvidia_model_uses_openai_compatible_endpoint_and_sample_settings(self):
        with patch.dict(
            "os.environ",
            {
                "NVIDIA_API_KEY": "offline-test-key",
                "NVIDIA_MODEL": "z-ai/glm-5.3-flash",
                "NVIDIA_TIMEOUT_SECONDS": "75",
            },
            clear=True,
        ):
            model = build_chat_model(PROVIDERS["2"])

        self.assertIsInstance(model, RunnableBinding)
        client = model.bound
        self.assertIsInstance(client, NvidiaChatOpenAI)
        self.assertEqual(client.root_client.base_url, "https://integrate.api.nvidia.com/v1/")
        self.assertEqual(client.model_name, "z-ai/glm-5.3-flash")
        self.assertEqual(client.temperature, 0.5)
        self.assertEqual(client.top_p, 1)
        self.assertEqual(client.root_client.timeout, 75)
        self.assertTrue(model.kwargs["parallel_tool_calls"])
        payload = client._get_request_payload([{"role": "user", "content": "test"}])
        self.assertEqual(payload["max_tokens"], 1024)
        self.assertNotIn("max_completion_tokens", payload)

    def test_openrouter_selection_keeps_reasoning_configuration(self):
        with patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "offline-test-key",
                "OPENROUTER_MODEL": "test/openrouter-model",
            },
            clear=True,
        ):
            model = build_chat_model(PROVIDERS["1"])
            selected_model = configured_model_name(PROVIDERS["1"])

        self.assertIsInstance(model, RunnableBinding)
        self.assertIsInstance(model.bound, OpenRouterChatOpenAI)
        self.assertEqual(
            model.bound.extra_body,
            {"reasoning": {"enabled": True}},
        )
        self.assertEqual(
            selected_model,
            "test/openrouter-model",
        )

    def test_missing_selected_provider_key_has_explicit_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "NVIDIA_API_KEY"):
                build_chat_model(PROVIDERS["2"])


if __name__ == "__main__":
    unittest.main()
