from __future__ import annotations


from ai.provider import AIProvider


AIResponse = tuple[str, str | None]


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
    ) -> AIResponse:
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
    def _normalize_finish_reason(reason: object | None) -> str | None:
        """
        Normalize provider-specific token-limit reasons.
        For OpenAI, the finish_reason can be "length" or "max_tokens".
        For Gemini, the finish_reason can be "max_output_tokens".
        For Claude, the finish_reason can be "max_tokens".

        """
        if reason is None:
            return None

        value = getattr(reason, "name", None) or getattr(reason, "value", reason)
        normalized = str(value).lower()
        if normalized in {"length", "max_tokens", "max_output_tokens"}:
            return "length"
        return normalized

    @staticmethod
    def _run_openai(
        api_key: str,
        model: str,
        input_text: str,
        system_prompt: str | None,
        max_tokens: int | None,
        temperature: float,
        timeout_seconds: int,
    ) -> AIResponse:
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

        choice = response.choices[0]
        return (
            choice.message.content or "",
            AIRunner._normalize_finish_reason(choice.finish_reason),
        )

    @staticmethod
    def _run_gemini(
        api_key: str,
        model: str,
        input_text: str,
        system_prompt: str | None,
        max_tokens: int | None,
        temperature: float,
    ) -> AIResponse:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents={"text": f"{system_prompt}\n\n{input_text}"},
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        candidate = response.candidates[0] if response.candidates else None
        return (
            response.text or "",
            AIRunner._normalize_finish_reason(
                candidate.finish_reason if candidate else None
            ),
        )

    @staticmethod
    def _run_claude(
        api_key: str,
        model: str,
        input_text: str,
        system_prompt: str | None,
        max_tokens: int | None,
        temperature: float,
        timeout_seconds: int,
    ) -> AIResponse:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key, timeout=timeout_seconds)
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": input_text}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (
            response.content[0].text,
            AIRunner._normalize_finish_reason(response.stop_reason),
        )

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
    ) -> AIResponse:
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
        choice = response.choices[0]
        return (
            choice.message.content or "",
            AIRunner._normalize_finish_reason(choice.finish_reason),
        )
