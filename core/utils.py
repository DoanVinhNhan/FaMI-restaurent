import json
import logging
from typing import Any, Optional, Union
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from .models import SystemSetting

logger = logging.getLogger(__name__)

class ConfigurationManager:
    """
    Singleton-like utility to manage system settings with caching and type casting.
    """
    
    _CACHE_TIMEOUT = 3600  # Cache settings for 1 hour
    _CACHE_PREFIX = "sys_setting_"

    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        """
        Retrieves a setting value by key.
        
        1. Checks Cache.
        2. Checks Database.
        3. Casts data based on `data_type`.
        4. Updates Cache.
        5. Returns default if not found or inactive.
        """
        cache_key = f"{cls._CACHE_PREFIX}{key}"
        cached_value = cache.get(cache_key)

        if cached_value is not None:
            return cached_value

        try:
            setting = SystemSetting.objects.get(pk=key)
            
            if not setting.is_active:
                return default

            value = cls._cast_value(setting.setting_value, setting.data_type)
            
            # Cache the casted value
            cache.set(cache_key, value, timeout=cls._CACHE_TIMEOUT)
            return value

        except ObjectDoesNotExist:
            logger.warning(f"Setting key '{key}' not found. Using default.")
            return default
        except Exception as e:
            logger.error(f"Error retrieving setting '{key}': {str(e)}")
            return default

    @classmethod
    def set_setting(cls, key: str, value: Any) -> bool:
        """
        Updates a setting value and invalidates the cache.
        Note: Does not create new settings, only updates existing ones to ensure strict control.
        """
        try:
            setting = SystemSetting.objects.get(pk=key)
            
            # Convert value back to string for storage
            if setting.data_type == SystemSetting.DataType.JSON:
                str_value = json.dumps(value)
            else:
                str_value = str(value)

            setting.setting_value = str_value
            setting.save()

            # Invalidate cache
            cache_key = f"{cls._CACHE_PREFIX}{key}"
            cache.delete(cache_key)
            
            return True
        except ObjectDoesNotExist:
            logger.error(f"Cannot update setting '{key}': Key does not exist.")
            return False
        except Exception as e:
            logger.error(f"Error updating setting '{key}': {str(e)}")
            return False

    @classmethod
    def reload_config(cls) -> None:
        """
        Clears all settings from cache.
        """
        # In a real production redis env, we might use pattern matching.
        # For simplicity, we assume keys are known or rely on TTL.
        # Here we just log, as deleting keys by pattern is backend-specific.
        cache.clear()
        logger.info("Configuration cache cleared.")

    @staticmethod
    def _cast_value(value: str, data_type: str) -> Union[str, int, float, bool, dict, list, None]:
        """
        Helper method to cast string values to their defined Python types.
        """
        try:
            if data_type == SystemSetting.DataType.INTEGER:
                return int(value)
            elif data_type == SystemSetting.DataType.FLOAT:
                return float(value)
            elif data_type == SystemSetting.DataType.BOOLEAN:
                return value.lower() in ('true', '1', 't', 'yes', 'on')
            elif data_type == SystemSetting.DataType.JSON:
                return json.loads(value)
            else:
                # Default to STRING
                return value
        except ValueError as e:
            logger.error(f"Type casting error for value '{value}' as {data_type}: {e}")
            return value  # Return raw string on failure
