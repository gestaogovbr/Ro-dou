from __future__ import annotations


from typing import Optional
from ai.provider import AIProvider


class AIRunner:
    """Runtime LLM execution logic (provider-agnostic)."""

    @staticmethod
    def run(
        provider: AIProvider,
        api_key: str,
        model: str,
        input_text: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.2,
        timeout_seconds: int = 60,
    ) -> str:
        if not api_key:
            raise RuntimeError("API_KEY not set")

        if provider == AIProvider.openai:
            return AIRunner._run_openai(
                api_key,
                model,
                input_text,
                system_prompt,
                max_tokens,
                temperature,
                timeout_seconds,
            )

        if provider == AIProvider.gemini:
            return AIRunner._run_gemini(
                api_key, model, input_text, system_prompt, max_tokens, temperature
            )

        if provider == AIProvider.claude:
            return AIRunner._run_claude(
                api_key,
                model,
                input_text,
                system_prompt,
                max_tokens,
                temperature,
                timeout_seconds,
            )

        if provider == AIProvider.azure:
            config = provider.get_azure_config(api_key)

            return AIRunner._run_azure(
                api_key,
                config["endpoint"],
                config["api_version"],
                config["deployment"],
                input_text,
                system_prompt,
                max_tokens,
                temperature,
                timeout_seconds,
            )

        raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def _run_openai(
        api_key: str,
        model: str,
        input_text: str,
        system_prompt: str | None,
        max_tokens: int | None,
        temperature: float,
        timeout_seconds: int,
    ) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=timeout_seconds)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input_text})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    @staticmethod
    def _run_gemini(
        api_key: str,
        model: str,
        input_text: str,
        system_prompt: str | None,
        max_tokens: int | None,
        temperature: float,
    ) -> str:
        from google import genai 
        from google.genai import types

        client=genai.Client(
            api_key = api_key
        )
        response = client.models.generate_content(
            model=model,
            contents={'text':system_prompt},
            config=types.GenerateContentConfig(
                temperature = temperature,
                max_output_tokens = max_tokens,
            ),
        )
        return response.text

    @staticmethod
    def _run_claude(
        api_key: str,
        model: str,
        input_text: str,
        system_prompt: str | None,
        max_tokens: int | None,
        temperature: float,
        timeout_seconds: int,
    ) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key, timeout=timeout_seconds)
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": input_text}],
            temperature=temperature,
            max_tokens=max_tokens or 1024,
        )
        return response.content[0].text

    @staticmethod
    def _run_azure(
        api_key: str,
        endpoint: str,
        api_version: str,
        deployment: str,
        input_text: str,
        system_prompt: str | None,
        max_tokens: int | None,
        temperature: float,
        timeout_seconds: int,
    ) -> str:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            timeout=timeout_seconds,
        )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input_text})

        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
