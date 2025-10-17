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

    # AlloyDB - Direct connection via public IP
    ALLOYDB_HOST: str = os.getenv("ALLOYDB_HOST", "")  # Public IP address of AlloyDB instance
    ALLOYDB_PORT: int = int(os.getenv("ALLOYDB_PORT", "5432"))
    ALLOYDB_DATABASE: str = os.getenv("ALLOYDB_DATABASE", "recipes")
    ALLOYDB_USER: str = os.getenv("ALLOYDB_USER", "")
    ALLOYDB_PASSWORD: str = os.getenv("ALLOYDB_PASSWORD", "")

    # Vertex AI
    VERTEX_AI_LOCATION: str = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    EMBEDDING_MODEL: str = "text-embedding-005"
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Application
    RESULT_LIMIT: int = int(os.getenv("RESULT_LIMIT", "2"))  # Default 2 results unless specified in query
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
            cls.ALLOYDB_HOST,
            cls.ALLOYDB_DATABASE,
            cls.ALLOYDB_USER,
            cls.ALLOYDB_PASSWORD,
        ]
        return all(required)


settings = Settings()
