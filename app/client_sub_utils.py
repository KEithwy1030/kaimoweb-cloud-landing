
import json
from functools import lru_cache
from typing import Dict, Any

from app.xui_client import xui_client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Simple cache dictionary
_inbound_settings_cache = {
    "data": None,
    "last_fetched": 0
}

def get_inbound_settings(inbound_id: int) -> Dict[str, Any]:
    """
    Fetches and parses inbound settings for subscription generation.
    Returns dictionary with key settings:
    - publicKey
    - shortId
    - serverName
    - fingerprint
    - flow (if present)
    - network (tcp/grpc/ws)
    - security (reality/tls/none)
    """
    import time
    
    # Check cache (1 hour expiry)
    now = time.time()
    if _inbound_settings_cache["data"] and (now - _inbound_settings_cache["last_fetched"] < 3600):
        return _inbound_settings_cache["data"]
        
    try:
        inbound = xui_client.get_inbound(inbound_id)
        if not inbound:
            logger.error(f"Failed to fetch inbound {inbound_id}")
            return {}
            
        stream_settings_str = inbound.get('streamSettings', '{}')
        try:
            stream_settings = json.loads(stream_settings_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse streamSettings JSON")
            return {}
            
        result = {}
        
        # General Network Info
        result['network'] = stream_settings.get('network', 'tcp')
        result['security'] = stream_settings.get('security', 'none')
        
        # Reality Settings
        if result['security'] == 'reality' or 'realitySettings' in stream_settings:
            reality = stream_settings.get('realitySettings', {})
            
            # Extract Public Key
            # First try settings.publicKey (common in standard X-UI)
            pk = reality.get('settings', {}).get('publicKey')
            if not pk:
                # Then try direct publicKey (3x-ui style)
                pk = reality.get('publicKey')
            
            result['publicKey'] = pk or ''

            # Extract Short IDs
            short_ids = reality.get('shortIds', [])
            if short_ids and isinstance(short_ids, list):
                result['shortId'] = short_ids[0]
            else:
                result['shortId'] = ''

            # Extract Server Names
            server_names = reality.get('serverNames', [])
            if server_names and isinstance(server_names, list) and len(server_names) > 0:
                result['serverName'] = server_names[0]
            else:
                # Fallback to dest if serverNames is empty
                dest = reality.get('dest', '')
                if ':' in dest:
                    result['serverName'] = dest.split(':')[0]
                else:
                    result['serverName'] = dest or 'google.com'

            result['fingerprint'] = reality.get('fingerprint', 'chrome')
            # result['flow'] = reality.get('flow', '') # Reality usually handles flow in higher level, but keeping it safe

            
        # Update Cache
        _inbound_settings_cache["data"] = result
        _inbound_settings_cache["last_fetched"] = now
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching inbound settings: {e}")
        return {}
