from enum import Enum
from airflow.models import Variable

class AIProvider(str, Enum):
    openai = "openai"
    gemini = "gemini"
    claude = "claude"
    azure = "azure"

    @classmethod
    def _missing_(cls, value):
    # Treat case-insensitively and allow matching by value
        if isinstance(value, str):
            value = value.lower()
            for member in cls:
                if member.value == value:
                    return member
        return None

    def get_azure_config(self, api_key: str) -> dict:
        if self != AIProvider.azure:
            raise ValueError("Azure config only applies to Azure provider")

        endpoint = Variable.get("AZURE_OPENAI_ENDPOINT", default_var=None)
        api_version = Variable.get("AZURE_OPENAI_API_VERSION", default_var=None)
        deployment = Variable.get("AZURE_OPENAI_DEPLOYMENT", default_var=None)

        if not all([api_key, endpoint, api_version, deployment]):
            raise RuntimeError(
                "Missing Azure env vars: "
                "AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT"
            )

        return {
            "endpoint": endpoint,
            "api_version": api_version,
            "deployment": deployment,
        }