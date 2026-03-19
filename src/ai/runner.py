from __future__ import annotations

from typing import Optional

class AIRunner:
    """Runtime LLM execution logic (provider-agnostic)."""

    @staticmethod
    def run(
        provider: str,
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

        if provider == "openai":
            return AIRunner._run_openai(
                api_key, model, input_text,
                system_prompt, max_tokens, temperature, timeout_seconds
            )

        if provider == "gemini":
            return AIRunner._run_gemini(
                api_key, model, input_text,
                system_prompt, max_tokens, temperature
            )

        if provider == "claude":
            return AIRunner._run_claude(
                api_key, model, input_text,
                system_prompt, max_tokens, temperature, timeout_seconds
            )

        if provider == "azure":
            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
            api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
            deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

            if not all([api_key, endpoint, api_version, deployment]):
                raise RuntimeError(
                    "Missing Azure env vars: "
                    "AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, "
                    "AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT"
                )

            return AIRunner._run_azure(
                api_key,
                endpoint,
                api_version,
                deployment,
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
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt}
                if system_prompt else None,
                {"role": "user", "content": input_text},
            ],
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        return response.output_text

    @staticmethod
    def _run_gemini(
        api_key: str,
        model: str,
        input_text: str,
        system_prompt: str | None,
        max_tokens: int | None,
        temperature: float,
    ) -> str:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model_client = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
        )
        response = model_client.generate_content(
            input_text,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
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
            messages=[
                {"role": "user", "content": input_text}
            ],
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

        response = client.responses.create(
            model=deployment,
            input=messages,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        return response.output_text