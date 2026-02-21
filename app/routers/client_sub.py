
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
import yaml
import json
import logging

from app.database import get_db
from app.models import Subscription, SystemConfig, Server
from app.client_sub_utils import get_inbound_settings
from app.config import settings

# Create a dedicated router for subscription downloads
router = APIRouter(tags=["Subscription Download"])

logger = logging.getLogger(__name__)

@router.get("/sub/{token}", summary="Download Subscription Config")
def download_subscription(token: str, db: Session = Depends(get_db)):
    """
    Download the Clash configuration for the given subscription token.
    Combines functionality of dynamic node list and custom template.
    """
    # 1. Validate Subscription
    sub = db.query(Subscription).filter(Subscription.token == token).first()
    if not sub:
        return Response(content="Subscription not found", status_code=404)
    
    if sub.is_expired():
        return Response(content="Subscription expired", status_code=403)
        
    if not sub.is_active:
        return Response(content="Subscription disabled", status_code=403)
        
    if not sub.xui_uuid:
        return Response(content="Subscription valid but not initialized (No UUID)", status_code=500)

    # 2. Fetch Template
    tpl_config = db.query(SystemConfig).filter(SystemConfig.key == "clash_template").first()
    if tpl_config and tpl_config.value:
        yaml_template = tpl_config.value
    else:
        # Fallback simple template if none exists
        yaml_template = """
port: 7890
socks-port: 7891
allow-lan: true
mode: Rule
log-level: info
external-controller: :9090
proxies: {proxies}
proxy-groups:
  - name: 🚀 Select
    type: select
    proxies: {node_names}
rules:
  - MATCH,🚀 Select
"""

    # 3. Fetch Node Information
    active_servers = db.query(Server).filter(Server.is_active == True).order_by(Server.sort_order).all()
    
    if not active_servers:
        # If no servers, return a dummy config or error
        return Response(content="# No active servers found", media_type="text/yaml")

    # 4. Get Reality/Inbound Config from X-UI (or cache)
    # We use a helper utility to avoid circular imports or complex logic here
    reality_config = get_inbound_settings(settings.XUI_INBOUND_ID)
    
    # 5. Build Proxy List
    proxies = []
    node_names = []
    
    for server in active_servers:
        # Determine protocol (assuming vless for now as per project context)
        # If server.type is different, handle accordingly.
        if server.type == 'vless':
            proxy = {
                "name": server.name,
                "type": "vless",
                "server": server.host,
                "port": server.port,
                "uuid": sub.xui_uuid,
                "network": "tcp",
                "tls": True,
                "udp": True,
                "flow": "", # standard vless usually empty unless vision
                "servername": reality_config.get('serverName', 'google.com'),
                "client-fingerprint": reality_config.get('fingerprint', 'chrome')
            }
            
            # Add Reality specifics if enabled
            if reality_config.get('publicKey'):
                proxy['reality-opts'] = {
                    "public-key": reality_config.get('publicKey'),
                    "short-id": reality_config.get('shortId', '')
                }
                # If using Reality, flow might be 'xtls-rprx-vision'
                # proxy['flow'] = 'xtls-rprx-vision' 
                
            proxies.append(proxy)
            node_names.append(server.name)
            
    # 6. Inject into Template
    # We use YAML dumping for the proxies list to ensure correct formatting
    proxies_yaml = yaml.dump(proxies, allow_unicode=True, sort_keys=False)
    
    # For node_names, we want a list format like ['A', 'B'], which matches the text replacement expectation
    # or we can dump it as a yaml list.
    # The template expects {node_names} to be inside a proxy list context usually.
    # If the template has `proxies: {node_names}`, proper YAML flow list `['A', 'B']` works.
    
    # Formatting node_names as a YAML flow sequence
    node_names_str = json.dumps(node_names, ensure_ascii=False)
    
    # Replace placeholders
    # {proxies} is usually indented in the template? 
    # yaml.dump output starts with "- name: ...". 
    # If the template is "proxies:\n{proxies}", it fits perfectly.
    # If {proxies} replacement is done via string replace, we need to ensure indentation matches?
    # Usually `proxies:` is at root, so indentation 0 for the keys, but the items are `-`.
    # yaml.dump produces root level items.
    
    final_yaml = yaml_template.replace("{proxies}", proxies_yaml)
    final_yaml = final_yaml.replace("{node_names}", node_names_str)
    
    # Add User Info Header
    user_info = f"# User: {sub.xui_email}\n# Upload: {sub.traffic_used_gb:.2f} GB\n# Total: {sub.traffic_total_gb} GB\n# Expire: {sub.expires_at}\n\n"
    final_yaml = user_info + final_yaml

    return Response(content=final_yaml, media_type="text/yaml")
