"""Configuration settings loaded from environment variables."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings."""

    # Google Cloud
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_SERVICE_ACCOUNT_JSON: str = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "")

    # AlloyDB
    ALLOYDB_INSTANCE: str = os.getenv("ALLOYDB_INSTANCE", "")
    ALLOYDB_CLUSTER: str = os.getenv("ALLOYDB_CLUSTER", "")
    ALLOYDB_REGION: str = os.getenv("ALLOYDB_REGION", "us-central1")
    ALLOYDB_DATABASE: str = os.getenv("ALLOYDB_DATABASE", "recipes")
    # For IAM auth, use service account email (e.g., my-sa@project.iam.gserviceaccount.com)
    ALLOYDB_USER: str = os.getenv("ALLOYDB_USER", "")

    # AlloyDB Auth Proxy settings
    ALLOYDB_PROXY_HOST: str = os.getenv("ALLOYDB_PROXY_HOST", "localhost")
    ALLOYDB_PROXY_PORT: int = int(os.getenv("ALLOYDB_PROXY_PORT", "5432"))

    # Vertex AI
    VERTEX_AI_LOCATION: str = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    EMBEDDING_MODEL: str = "text-embedding-005"
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Application
    RESULT_LIMIT: int = int(os.getenv("RESULT_LIMIT", "10"))
    SESSION_MEMORY_SIZE: int = int(os.getenv("SESSION_MEMORY_SIZE", "10"))
    RESPONSE_TIMEOUT_SECONDS: int = int(os.getenv("RESPONSE_TIMEOUT_SECONDS", "10"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Ranking weights
    SIMILARITY_WEIGHT: float = 0.6
    RATING_WEIGHT: float = 0.3
    RATING_COUNT_WEIGHT: float = 0.1

    # TM6 version filter
    THERMOMIX_VERSION: str = "TM6"

    @classmethod
    def validate(cls) -> bool:
        """Validate required settings are present."""
        required = [
            cls.GCP_PROJECT_ID,
            cls.GCP_SERVICE_ACCOUNT_JSON,
            cls.ALLOYDB_INSTANCE,
            cls.ALLOYDB_DATABASE,
            cls.ALLOYDB_USER,
        ]
        return all(required)


settings = Settings()
