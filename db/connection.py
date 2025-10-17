"""AlloyDB connection manager with retry logic."""

import os
import time
import logging
import pg8000
from config.settings import settings

logger = logging.getLogger(__name__)


class AlloyDBConnection:
    """Manages AlloyDB database connections using public IP."""

    def __init__(self):
        """Initialize the connection manager."""
        self._validated = False

    def connect_with_retry(self) -> None:
        """
        Establish connection to AlloyDB using public IP.

        Connects directly to AlloyDB instance via public IP address.
        Requires AlloyDB instance to have public IP enabled.
        Implements retry logic for network connectivity issues.
        """
        for attempt in range(settings.MAX_RETRIES):
            try:
                logger.info(f"Attempting to connect to AlloyDB (attempt {attempt + 1}/{settings.MAX_RETRIES})")
                logger.info(f"Host: {settings.ALLOYDB_HOST}")
                logger.info(f"Port: {settings.ALLOYDB_PORT}")
                logger.info(f"Database: {settings.ALLOYDB_DATABASE}")
                logger.info(f"User: {settings.ALLOYDB_USER}")

                # Connect to AlloyDB using public IP
                import socket
                original_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(5.0)

                try:
                    logger.debug(f"Connecting to AlloyDB at {settings.ALLOYDB_HOST}:{settings.ALLOYDB_PORT}...")
                    conn = pg8000.connect(
                        host=settings.ALLOYDB_HOST,
                        port=settings.ALLOYDB_PORT,
                        database=settings.ALLOYDB_DATABASE,
                        user=settings.ALLOYDB_USER,
                        password=settings.ALLOYDB_PASSWORD,
                        timeout=5,
                        ssl_context=True,  # Enable SSL for public IP connections
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

                logger.info("Successfully connected to AlloyDB via public IP")
                return

            except socket.timeout as e:
                logger.error(f"Connection timeout after 5 seconds (attempt {attempt + 1})")
                logger.error(f"Timeout error details: {type(e).__name__}: {str(e)}")
                logger.error("Possible causes:")
                logger.error(f"  1. AlloyDB public IP not accessible from your network")
                logger.error(f"  2. Firewall blocking connection to {settings.ALLOYDB_HOST}:{settings.ALLOYDB_PORT}")
                logger.error("  3. VPN issues or network connectivity problems")
                logger.error("  4. AlloyDB instance not running or public IP not enabled")

                if attempt < settings.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise ConnectionError(
                        f"Failed to connect to AlloyDB after {settings.MAX_RETRIES} attempts: Connection timeout after 5 seconds. "
                        f"Check firewall rules and ensure AlloyDB public IP is enabled."
                    )

            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {repr(e)}")

                # Log additional context for specific error types
                if "connection refused" in str(e).lower():
                    logger.error("Connection refused error. Check:")
                    logger.error(f"  1. AlloyDB instance is running")
                    logger.error(f"  2. Public IP is enabled on the instance")
                    logger.error(f"  3. Host and port are correct: {settings.ALLOYDB_HOST}:{settings.ALLOYDB_PORT}")
                    logger.error("  4. Firewall allows connections from your IP")
                elif "authentication" in str(e).lower() or "password" in str(e).lower():
                    logger.error("Authentication error detected. Check:")
                    logger.error("  1. Username is correct")
                    logger.error("  2. Password is correct")
                    logger.error("  3. User has permission to access the database")
                    logger.error("  4. SSL settings are correct")
                elif "no route to host" in str(e).lower() or "network unreachable" in str(e).lower():
                    logger.error("Network error. Verify:")
                    logger.error(f"  1. AlloyDB public IP address is correct: {settings.ALLOYDB_HOST}")
                    logger.error("  2. VPN connection is active")
                    logger.error("  3. Network can reach Google Cloud")

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
        Get a new connection using public IP.

        Returns:
            Database connection object
        """
        try:
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(5.0)

            try:
                logger.debug(f"Getting new connection to {settings.ALLOYDB_HOST}:{settings.ALLOYDB_PORT}")
                conn = pg8000.connect(
                    host=settings.ALLOYDB_HOST,
                    port=settings.ALLOYDB_PORT,
                    database=settings.ALLOYDB_DATABASE,
                    user=settings.ALLOYDB_USER,
                    password=settings.ALLOYDB_PASSWORD,
                    timeout=5,
                    ssl_context=True,
                )
                logger.debug("Connection obtained successfully")
                return conn
            finally:
                socket.setdefaulttimeout(original_timeout)

        except socket.timeout as e:
            logger.error(f"Connection timeout after 5 seconds: {str(e)}")
            logger.error(f"Check network connectivity to {settings.ALLOYDB_HOST}")
            raise ConnectionError(f"Connection timeout after 5 seconds. Check VPN and network connectivity.")
        except Exception as e:
            logger.error(f"Failed to get connection: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            if "connection refused" in str(e).lower():
                logger.error(f"Connection refused. Check if AlloyDB is accessible at {settings.ALLOYDB_HOST}:{settings.ALLOYDB_PORT}")
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
        """Close any resources (no-op when using direct connections)."""
        # Connections are closed individually
        # No global connector to close
        logger.info("Connection manager shutdown")


# Global connection instance
db_connection = AlloyDBConnection()
