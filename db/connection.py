"""AlloyDB connection manager with retry logic."""

import os
import time
import logging
from typing import Optional
import pg8000
from google.oauth2 import service_account
from config.settings import settings

logger = logging.getLogger(__name__)


class AlloyDBConnection:
    """Manages AlloyDB database connections with IAM authentication via Auth Proxy."""

    def __init__(self):
        """Initialize the connection manager."""
        self._validated = False
        self.proxy_host = settings.ALLOYDB_PROXY_HOST if hasattr(settings, 'ALLOYDB_PROXY_HOST') else 'localhost'
        self.proxy_port = settings.ALLOYDB_PROXY_PORT if hasattr(settings, 'ALLOYDB_PROXY_PORT') else 5432

    def _get_instance_connection_name(self) -> str:
        """
        Build AlloyDB instance connection name for proxy.

        Format: projects/PROJECT_ID/locations/REGION/clusters/CLUSTER/instances/INSTANCE
        """
        connection_name = (
            f"projects/{settings.GCP_PROJECT_ID}/"
            f"locations/{settings.ALLOYDB_REGION}/"
            f"clusters/{settings.ALLOYDB_CLUSTER}/"
            f"instances/{settings.ALLOYDB_INSTANCE}"
        )
        logger.debug(f"Instance connection name: {connection_name}")
        return connection_name

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
        Establish connection to AlloyDB via Auth Proxy with IAM authentication.

        Connects through AlloyDB Auth Proxy running locally.
        Requires proxy to be started with: ./alloydb-auth-proxy <instance-uri>
        Implements retry logic for VPN connectivity issues.
        """
        for attempt in range(settings.MAX_RETRIES):
            try:
                logger.info(f"Attempting to connect to AlloyDB via proxy (attempt {attempt + 1}/{settings.MAX_RETRIES})")
                logger.info(f"Proxy: {self.proxy_host}:{self.proxy_port}")
                logger.info(f"Project: {settings.GCP_PROJECT_ID}")
                logger.info(f"Region: {settings.ALLOYDB_REGION}")
                logger.info(f"Cluster: {settings.ALLOYDB_CLUSTER}")
                logger.info(f"Instance: {settings.ALLOYDB_INSTANCE}")
                logger.info(f"Database: {settings.ALLOYDB_DATABASE}")
                logger.info(f"User: {settings.ALLOYDB_USER}")

                logger.debug(f"Expected proxy command: ./alloydb-auth-proxy {self._get_instance_connection_name()}")

                # Connect to AlloyDB through the proxy
                # The proxy handles IAM authentication
                import socket
                original_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(5.0)

                try:
                    logger.debug(f"Connecting to proxy at {self.proxy_host}:{self.proxy_port}...")
                    conn = pg8000.connect(
                        host=self.proxy_host,
                        port=self.proxy_port,
                        database=settings.ALLOYDB_DATABASE,
                        user=settings.ALLOYDB_USER,
                        timeout=5,
                    )
                    logger.debug("Connection object created successfully")
                finally:
                    socket.setdefaulttimeout(original_timeout)

                # Test the connection with a simple query
                logger.debug("Testing connection with simple query...")
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                logger.debug(f"Test query result: {result}")

                # Close test connection
                logger.debug("Closing test connection...")
                conn.close()
                logger.debug("Test connection closed")

                logger.info("Successfully connected to AlloyDB via Auth Proxy using IAM authentication")
                return

            except socket.timeout as e:
                logger.error(f"Connection timeout after 5 seconds (attempt {attempt + 1})")
                logger.error(f"Timeout error details: {type(e).__name__}: {str(e)}")
                logger.error("Possible causes:")
                logger.error("  1. AlloyDB Auth Proxy not running")
                logger.error(f"  2. Proxy not listening on {self.proxy_host}:{self.proxy_port}")
                logger.error("  3. VPN issues or network connectivity problems")
                logger.error(f"\nStart the proxy with: ./alloydb-auth-proxy {self._get_instance_connection_name()}")

                if attempt < settings.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise ConnectionError(
                        f"Failed to connect to AlloyDB after {settings.MAX_RETRIES} attempts: Connection timeout after 5 seconds. "
                        f"Ensure AlloyDB Auth Proxy is running: ./alloydb-auth-proxy {self._get_instance_connection_name()}"
                    )

            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {repr(e)}")

                # Log additional context for specific error types
                if "connection refused" in str(e).lower():
                    logger.error("Connection refused error. Check:")
                    logger.error(f"  1. AlloyDB Auth Proxy is running on {self.proxy_host}:{self.proxy_port}")
                    logger.error(f"  2. Start proxy: ./alloydb-auth-proxy {self._get_instance_connection_name()}")
                    logger.error("  3. Proxy is bound to the correct port")
                elif "authentication" in str(e).lower() or "permission" in str(e).lower():
                    logger.error("Authentication error detected. Check:")
                    logger.error("  1. AlloyDB Auth Proxy started with correct service account credentials")
                    logger.error("  2. Service account has 'roles/alloydb.client' IAM role")
                    logger.error("  3. IAM database user exists in AlloyDB")
                    logger.error("  4. Database user has necessary privileges")
                elif "no such file or directory" in str(e).lower() or "host" in str(e).lower():
                    logger.error("Host/socket error. Verify:")
                    logger.error(f"  1. Proxy is running and listening on {self.proxy_host}:{self.proxy_port}")
                    logger.error(f"  2. Start proxy: ./alloydb-auth-proxy {self._get_instance_connection_name()}")

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
        Get a new connection via Auth Proxy using IAM authentication.

        Returns:
            Database connection object
        """
        try:
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(5.0)

            try:
                logger.debug(f"Getting new connection via proxy at {self.proxy_host}:{self.proxy_port}")
                conn = pg8000.connect(
                    host=self.proxy_host,
                    port=self.proxy_port,
                    database=settings.ALLOYDB_DATABASE,
                    user=settings.ALLOYDB_USER,
                    timeout=5,
                )
                logger.debug("Connection obtained successfully")
                return conn
            finally:
                socket.setdefaulttimeout(original_timeout)

        except socket.timeout as e:
            logger.error(f"Connection timeout after 5 seconds: {str(e)}")
            logger.error(f"Ensure AlloyDB Auth Proxy is running: ./alloydb-auth-proxy {self._get_instance_connection_name()}")
            raise ConnectionError(f"Connection timeout after 5 seconds. Check proxy is running and VPN connectivity.")
        except Exception as e:
            logger.error(f"Failed to get connection: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            if "connection refused" in str(e).lower():
                logger.error(f"Proxy not running. Start with: ./alloydb-auth-proxy {self._get_instance_connection_name()}")
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
        """Close any resources (no-op when using proxy)."""
        # When using Auth Proxy, connections are closed individually
        # No global connector to close
        logger.info("Connection manager shutdown (proxy-based connections)")


# Global connection instance
db_connection = AlloyDBConnection()
