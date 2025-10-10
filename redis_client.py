import logging
import os
from dotenv import load_dotenv
import redis # type: ignore
# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.client = None
        self.is_available = False
        
        try:
            self.client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"), 
                port=int(os.getenv("REDIS_PORT", 6379)), 
                db=int(os.getenv("REDIS_DB", 0)), 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test the connection
            self.client.ping()
            self.is_available = True
            logger.info("✅ Redis connection established successfully")
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Redis connection failed: {str(e)}")
            logger.warning("⚠️ Redis is not available - application will run without caching")
            self.client = None
            self.is_available = False
        except Exception as e:
            logger.warning(f"⚠️ Unexpected error connecting to Redis: {str(e)}")
            logger.warning("⚠️ Redis is not available - application will run without caching")
            self.client = None
            self.is_available = False

    def setex(self, key, expiry_seconds, value):
        """Set the value of the key in Redis with an expiry time"""
        if not self.is_available:
            logger.debug(f"Redis not available - skipping setex for key: {key}")
            return False
            
        try:
            self.client.setex(key, expiry_seconds, value)
            logger.info(f"Successfully set key: {key}")
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error setting key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting key {key}: {str(e)}")
            return False

    def get(self, key):
        """Get the value of the key from Redis"""
        if not self.is_available:
            logger.debug(f"Redis not available - skipping get for key: {key}")
            return None
            
        try:
            value = self.client.get(key)
            logger.info(f"Retrieved key: {key}, found: {value is not None}")
            return value
        except redis.RedisError as e:
            logger.error(f"Redis error getting key {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting key {key}: {str(e)}")
            return None

    def delete(self, key):
        """Delete the key from Redis"""
        if not self.is_available:
            logger.debug(f"Redis not available - skipping delete for key: {key}")
            return False
            
        try:
            result = self.client.delete(key)
            success = bool(result)
            logger.info(f"Deleted key: {key}, success: {success}")
            return result
        except redis.RedisError as e:
            logger.error(f"Redis error deleting key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting key {key}: {str(e)}")
            return False
            
    def exists(self, key):
        """Check if key exists in Redis"""
        if not self.is_available:
            logger.debug(f"Redis not available - skipping exists for key: {key}")
            return False
            
        try:
            result = self.client.exists(key)
            return bool(result)
        except redis.RedisError as e:
            logger.error(f"Redis error checking key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking key {key}: {str(e)}")
            raise