"""OpenRouter-compatible LangChain chat model with reasoning metadata replay."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.messages.utils import convert_to_messages
from langchain_openai import ChatOpenAI


class OpenRouterChatOpenAI(ChatOpenAI):
    """Preserve OpenRouter reasoning_details across LangChain agent turns."""

    def _create_chat_result(
        self,
        response: Any,
        generation_info: dict[str, Any] | None = None,
    ) -> Any:
        result = super()._create_chat_result(response, generation_info)
        if isinstance(response, dict):
            response_data = response
        elif hasattr(response, "model_dump"):
            response_data = response.model_dump(exclude_none=True)
        else:
            return result

        choices = response_data.get("choices") or []
        for generation, choice in zip(result.generations, choices):
            message = generation.message
            reasoning_details = choice.get("message", {}).get("reasoning_details")
            if isinstance(message, AIMessage) and reasoning_details is not None:
                message.additional_kwargs["reasoning_details"] = reasoning_details
        return result

    def _get_request_payload(
        self,
        input_: Any,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        input_messages: list[BaseMessage] = convert_to_messages(input_)
        request_messages = payload.get("messages", [])

        for source, target in zip(input_messages, request_messages):
            if not isinstance(source, AIMessage):
                continue
            reasoning_details = source.additional_kwargs.get("reasoning_details")
            if reasoning_details is not None and target.get("role") == "assistant":
                target["reasoning_details"] = reasoning_details
        return payload
