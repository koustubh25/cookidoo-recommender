"""AlloyDB connection manager with retry logic."""

import os
import time
import logging
from typing import Optional
from google.cloud.sql.connector import Connector
from google.auth import default
from google.oauth2 import service_account
import pg8000
from config.settings import settings

logger = logging.getLogger(__name__)


class AlloyDBConnection:
    """Manages AlloyDB database connections with IAM authentication."""

    def __init__(self):
        """Initialize the connection manager."""
        self.connector: Optional[Connector] = None
        self._validated = False

    def _get_connection_string(self) -> str:
        """Build AlloyDB connection string."""
        return (
            f"projects/{settings.GCP_PROJECT_ID}/"
            f"locations/{settings.ALLOYDB_REGION}/"
            f"clusters/{settings.ALLOYDB_CLUSTER}/"
            f"instances/{settings.ALLOYDB_INSTANCE}"
        )

    def _get_credentials(self):
        """Get service account credentials for IAM authentication."""
        if settings.GCP_SERVICE_ACCOUNT_JSON and os.path.exists(settings.GCP_SERVICE_ACCOUNT_JSON):
            credentials = service_account.Credentials.from_service_account_file(
                settings.GCP_SERVICE_ACCOUNT_JSON,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            logger.info("Using service account credentials from JSON file")
            return credentials
        else:
            # Fall back to application default credentials
            credentials, project = default()
            logger.info("Using application default credentials")
            return credentials

    def connect_with_retry(self) -> None:
        """
        Establish connection to AlloyDB with IAM authentication and exponential backoff retry.

        Uses service account from GCP_SERVICE_ACCOUNT_JSON for IAM authentication.
        Implements retry logic for VPN connectivity issues.
        """
        for attempt in range(settings.MAX_RETRIES):
            try:
                logger.info(f"Attempting to connect to AlloyDB (attempt {attempt + 1}/{settings.MAX_RETRIES})")

                # Get credentials for IAM authentication
                credentials = self._get_credentials()

                # Initialize the Cloud SQL Python Connector with IAM auth
                self.connector = Connector(credentials=credentials)

                # Test connection
                conn = self.connector.connect(
                    self._get_connection_string(),
                    "pg8000",
                    user=settings.ALLOYDB_USER,  # Service account email without @domain
                    db=settings.ALLOYDB_DATABASE,
                    enable_iam_auth=True,  # Enable IAM authentication
                )

                # Close test connection
                conn.close()

                logger.info("Successfully connected to AlloyDB using IAM authentication")
                return

            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")

                if attempt < settings.MAX_RETRIES - 1:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise ConnectionError(
                        f"Failed to connect to AlloyDB after {settings.MAX_RETRIES} attempts: {str(e)}"
                    )

    def get_connection(self):
        """
        Get a new connection using IAM authentication.

        Returns:
            Database connection object
        """
        if not self.connector:
            raise RuntimeError("Connector not initialized. Call connect_with_retry() first.")

        try:
            conn = self.connector.connect(
                self._get_connection_string(),
                "pg8000",
                user=settings.ALLOYDB_USER,
                db=settings.ALLOYDB_DATABASE,
                enable_iam_auth=True,
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection: {str(e)}")
            raise

    def return_connection(self, conn):
        """
        Close and return a connection.

        Args:
            conn: Database connection to close
        """
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {str(e)}")

    def validate_connection(self) -> bool:
        """
        Validate database connectivity and check embedding dimensions.

        Returns:
            bool: True if connection and schema are valid.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Check if vector extension exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                );
            """)
            has_vector = cursor.fetchone()[0]

            if not has_vector:
                logger.error("Vector extension not found in database")
                cursor.close()
                self.return_connection(conn)
                return False

            # Check embedding dimensions
            cursor.execute("""
                SELECT vector_dims(embedding) as dims
                FROM recipes
                WHERE embedding IS NOT NULL
                LIMIT 1;
            """)
            result = cursor.fetchone()

            if not result:
                logger.warning("No recipes with embeddings found")
                cursor.close()
                self.return_connection(conn)
                return True  # Connection OK, just no data yet

            dims = result[0]
            expected_dims = 768

            if dims != expected_dims:
                logger.error(f"Embedding dimension mismatch: expected {expected_dims}, got {dims}")
                cursor.close()
                self.return_connection(conn)
                return False

            logger.info(f"Connection validated. Embedding dimensions: {dims}")
            cursor.close()
            self.return_connection(conn)
            self._validated = True
            return True

        except Exception as e:
            logger.error(f"Connection validation failed: {str(e)}")
            return False

    def close(self):
        """Close the connector."""
        if self.connector:
            try:
                self.connector.close()
                logger.info("Database connector closed")
            except Exception as e:
                logger.warning(f"Error closing connector: {str(e)}")


# Global connection instance
db_connection = AlloyDBConnection()
