"""AlloyDB connection manager with retry logic."""

import os
import time
import logging
from typing import Optional
import pg8000
from google.cloud.alloydb.connector import Connector
from google.oauth2 import service_account
from config.settings import settings

logger = logging.getLogger(__name__)


class AlloyDBConnection:
    """Manages AlloyDB database connections with IAM authentication."""

    def __init__(self):
        """Initialize the connection manager."""
        self.connector: Optional[Connector] = None
        self._validated = False

    def _get_instance_uri(self) -> str:
        """
        Build AlloyDB instance URI.

        Format: projects/PROJECT_ID/locations/REGION/clusters/CLUSTER/instances/INSTANCE
        """
        instance_uri = (
            f"projects/{settings.GCP_PROJECT_ID}/"
            f"locations/{settings.ALLOYDB_REGION}/"
            f"clusters/{settings.ALLOYDB_CLUSTER}/"
            f"instances/{settings.ALLOYDB_INSTANCE}"
        )
        logger.debug(f"Instance URI: {instance_uri}")
        return instance_uri

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
            raise ValueError("Service account JSON file not found. Please set GCP_SERVICE_ACCOUNT_JSON.")

    def connect_with_retry(self) -> None:
        """
        Establish connection to AlloyDB with IAM authentication and exponential backoff retry.

        Uses service account from GCP_SERVICE_ACCOUNT_JSON for IAM authentication.
        Implements retry logic for VPN connectivity issues.
        """
        for attempt in range(settings.MAX_RETRIES):
            try:
                logger.info(f"Attempting to connect to AlloyDB (attempt {attempt + 1}/{settings.MAX_RETRIES})")
                logger.info(f"Project: {settings.GCP_PROJECT_ID}")
                logger.info(f"Region: {settings.ALLOYDB_REGION}")
                logger.info(f"Cluster: {settings.ALLOYDB_CLUSTER}")
                logger.info(f"Instance: {settings.ALLOYDB_INSTANCE}")
                logger.info(f"Database: {settings.ALLOYDB_DATABASE}")
                logger.info(f"User: {settings.ALLOYDB_USER}")

                # Get credentials for IAM authentication
                logger.debug("Loading service account credentials...")
                credentials = self._get_credentials()
                logger.debug(f"Credentials loaded. Service account: {credentials.service_account_email if hasattr(credentials, 'service_account_email') else 'N/A'}")

                # Initialize the AlloyDB Connector with IAM auth
                logger.debug("Initializing AlloyDB Connector...")
                self.connector = Connector(credentials=credentials)
                logger.debug("Connector initialized successfully")

                instance_uri = self._get_instance_uri()
                logger.debug(f"Connecting to instance URI: {instance_uri}")
                logger.debug(f"Connection parameters: driver=pg8000, user={settings.ALLOYDB_USER}, db={settings.ALLOYDB_DATABASE}, enable_iam_auth=True, timeout=5s")

                # Test connection with 5 second timeout
                import socket
                original_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(5.0)

                try:
                    conn = self.connector.connect(
                        instance_uri,
                        "pg8000",
                        user=settings.ALLOYDB_USER,
                        db=settings.ALLOYDB_DATABASE,
                        enable_iam_auth=True,
                        timeout=5,
                    )
                    logger.debug("Connection object created successfully")
                finally:
                    socket.setdefaulttimeout(original_timeout)

                # Close test connection
                logger.debug("Closing test connection...")
                conn.close()
                logger.debug("Test connection closed")

                logger.info("Successfully connected to AlloyDB using IAM authentication")
                return

            except socket.timeout as e:
                logger.error(f"Connection timeout after 5 seconds (attempt {attempt + 1})")
                logger.error(f"Timeout error details: {type(e).__name__}: {str(e)}")
                logger.error("Possible causes: VPN issues, firewall blocking connection, incorrect instance URI, network latency")

                if attempt < settings.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise ConnectionError(
                        f"Failed to connect to AlloyDB after {settings.MAX_RETRIES} attempts: Connection timeout after 5 seconds. "
                        f"Check VPN connection, firewall rules, and instance URI: {self._get_instance_uri()}"
                    )

            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {repr(e)}")

                # Log additional context for specific error types
                if "authentication" in str(e).lower() or "permission" in str(e).lower():
                    logger.error("Authentication error detected. Check:")
                    logger.error("  1. Service account has 'roles/alloydb.client' IAM role")
                    logger.error("  2. IAM database user exists in AlloyDB")
                    logger.error("  3. Database user has necessary privileges")
                elif "not found" in str(e).lower() or "does not exist" in str(e).lower():
                    logger.error("Resource not found error. Verify:")
                    logger.error(f"  Instance URI: {self._get_instance_uri()}")
                    logger.error("  Instance exists and is in READY state")
                    logger.error("  Region, cluster, and instance names are correct")
                elif "api" in str(e).lower():
                    logger.error("API error detected. Ensure:")
                    logger.error("  AlloyDB API is enabled in project")
                    logger.error("  Service account has proper API access")

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
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(5.0)

            try:
                logger.debug(f"Getting new connection to {self._get_instance_uri()}")
                conn = self.connector.connect(
                    self._get_instance_uri(),
                    "pg8000",
                    user=settings.ALLOYDB_USER,
                    db=settings.ALLOYDB_DATABASE,
                    enable_iam_auth=True,
                    timeout=5,
                )
                logger.debug("Connection obtained successfully")
                return conn
            finally:
                socket.setdefaulttimeout(original_timeout)

        except socket.timeout as e:
            logger.error(f"Connection timeout after 5 seconds: {str(e)}")
            raise ConnectionError(f"Connection timeout after 5 seconds. Check VPN and network connectivity.")
        except Exception as e:
            logger.error(f"Failed to get connection: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
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

    async def close_async(self):
        """Async close the connector."""
        if self.connector:
            try:
                await self.connector.close_async()
                logger.info("Database connector closed")
            except Exception as e:
                logger.warning(f"Error closing connector: {str(e)}")

    def close(self):
        """Close the connector synchronously."""
        if self.connector:
            try:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, schedule the close
                        asyncio.create_task(self.connector.close_async())
                    else:
                        # If loop is not running, run it
                        loop.run_until_complete(self.connector.close_async())
                except RuntimeError:
                    # No event loop, create one
                    asyncio.run(self.connector.close_async())
                logger.info("Database connector closed")
            except Exception as e:
                logger.warning(f"Error closing connector: {str(e)}")


# Global connection instance
db_connection = AlloyDBConnection()
