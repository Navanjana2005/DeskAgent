"""Provider selection and OpenAI-compatible chat model construction."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.language_models import LanguageModelInput
from langchain_openai import ChatOpenAI

from openrouter import OpenRouterChatOpenAI


@dataclass(frozen=True)
class ProviderConfig:
    key: str
    label: str
    base_url: str
    api_key_env: str
    model_env: str
    default_model: str
    timeout_env: str
    temperature: float
    top_p: float
    max_completion_tokens: int
    reasoning_enabled: bool = False
    seed: int | None = None


class NvidiaChatOpenAI(ChatOpenAI):
    """Adapt LangChain's token limit field to NVIDIA's max_tokens parameter."""

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        completion_limit = payload.pop("max_completion_tokens", None)
        if completion_limit is not None:
            payload["max_tokens"] = completion_limit
        return payload


PROVIDERS = {
    "1": ProviderConfig(
        key="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_env="OPENROUTER_MODEL",
        default_model="nvidia/nemotron-3-ultra-550b-a55b:free",
        timeout_env="OPENROUTER_TIMEOUT_SECONDS",
        temperature=1,
        top_p=0.95,
        max_completion_tokens=16384,
        reasoning_enabled=True,
        seed=42,
    ),
    "2": ProviderConfig(
        key="nvidia",
        label="NVIDIA",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        model_env="NVIDIA_MODEL",
        default_model="z-ai/glm-5.3-flash",
        timeout_env="NVIDIA_TIMEOUT_SECONDS",
        temperature=0.5,
        top_p=1,
        max_completion_tokens=1024,
    ),
}


def select_provider(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> ProviderConfig:
    """Prompt until the user selects a supported provider."""
    while True:
        output_fn("Choose your LLM API endpoint:")
        output_fn("  1) OpenRouter")
        output_fn("  2) NVIDIA")
        selection = input_fn("Select endpoint [1/2]: ").strip()
        provider = PROVIDERS.get(selection)
        if provider is not None:
            return provider
        output_fn("Invalid selection. Enter 1 for OpenRouter or 2 for NVIDIA.")


def configured_model_name(provider: ProviderConfig) -> str:
    return os.getenv(provider.model_env, provider.default_model)


def build_chat_model(provider: ProviderConfig) -> ChatOpenAI:
    """Build the selected provider client using its own key and model settings."""
    api_key = os.getenv(provider.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"{provider.api_key_env} is not set. Add the selected provider's "
            "API key to your .env file."
        )

    timeout_value = os.getenv(provider.timeout_env, "180")
    try:
        timeout_seconds = int(timeout_value)
    except ValueError as error:
        raise RuntimeError(f"{provider.timeout_env} must be a positive integer.") from error
    if timeout_seconds <= 0:
        raise RuntimeError(f"{provider.timeout_env} must be a positive integer.")

    model_options: dict[str, Any] = {
        "base_url": provider.base_url,
        "model": configured_model_name(provider),
        "api_key": api_key,
        "temperature": provider.temperature,
        "top_p": provider.top_p,
        "max_completion_tokens": provider.max_completion_tokens,
        "timeout": timeout_seconds,
    }
    if provider.seed is not None:
        model_options["seed"] = provider.seed

    if provider.reasoning_enabled:
        model = OpenRouterChatOpenAI(
            **model_options,
            extra_body={"reasoning": {"enabled": True}},
        )
    else:
        model = NvidiaChatOpenAI(**model_options)
    return model.bind(parallel_tool_calls=True)
