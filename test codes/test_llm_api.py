"""Test the OpenRouter reasoning flow or a NVIDIA completion."""

import os
import sys
import argparse
from typing import Any

import dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)


PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "timeout_env": "OPENROUTER_TIMEOUT_SECONDS",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "model_env": "NVIDIA_MODEL",
        "default_model": "z-ai/glm-5.3-flash",
        "timeout_env": "NVIDIA_TIMEOUT_SECONDS",
    },
}
FIRST_PROMPT = "How many r's are in the word 'strawberry'?"


def main() -> int:
    dotenv.load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default="openrouter",
        help="API endpoint to test (default: openrouter)",
    )
    args = parser.parse_args()
    provider = PROVIDERS[args.provider]

    api_key = os.getenv(provider["api_key_env"])
    if not api_key:
        print(
            f"{provider['api_key_env']} is missing. "
            "Add the selected provider's key to .env."
        )
        return 2

    try:
        timeout_seconds = int(os.getenv(provider["timeout_env"], "180"))
    except ValueError:
        print(f"{provider['timeout_env']} must be a positive integer.")
        return 2
    if timeout_seconds <= 0:
        print(f"{provider['timeout_env']} must be a positive integer.")
        return 2

    client = OpenAI(
        base_url=provider["base_url"],
        api_key=api_key,
        timeout=timeout_seconds,
    )
    model = os.getenv(provider["model_env"], provider["default_model"])

    try:
        if args.provider == "nvidia":
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {
                        "role": "user",
                        "content": "Which number is larger, 9.11 or 9.8?",
                    },
                ],
                temperature=0.5,
                top_p=1,
                max_tokens=1024,
                stream=False,
            )
            print(completion.choices[0].message)
            print("\nNVIDIA API request completed.")
            return 0

        reasoning = {"reasoning": {"enabled": True}}
        first_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": FIRST_PROMPT}],
            extra_body=reasoning,
            max_tokens=1024,
        ).choices[0].message

        # OpenRouter requires these provider details to be passed back unchanged.
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": first_response.content,
        }
        reasoning_details = getattr(first_response, "reasoning_details", None)
        if reasoning_details is not None:
            assistant_message["reasoning_details"] = reasoning_details

        messages = [
            {"role": "user", "content": FIRST_PROMPT},
            assistant_message,
            {"role": "user", "content": "Are you sure? Think carefully."},
        ]
        second_response = client.chat.completions.create(
            model=model,
            messages=messages,
            extra_body=reasoning,
            max_tokens=1024,
        ).choices[0].message

        print("First response:", first_response.content or "(empty response)")
        print("Second response:", second_response.content or "(empty response)")
        return 0
    except AuthenticationError:
        print(f"{args.provider} rejected the API key. Check {provider['api_key_env']}.")
    except RateLimitError:
        print(f"{args.provider} rate limit or model quota reached. Try again later.")
    except APITimeoutError:
        print(
            f"{args.provider} did not respond within {timeout_seconds}s. "
            "This does not determine whether the API key is valid."
        )
    except APIConnectionError as error:
        print(f"Could not connect to {args.provider}: {type(error).__name__}.")
    except APIStatusError as error:
        print(f"{args.provider} returned HTTP {error.status_code}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
