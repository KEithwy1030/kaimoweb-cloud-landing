
import yaml
import sys
import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Database setup
DATABASE_URL = "sqlite:///./vpn_distribution.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redefine SystemConfig locally to avoid import issues
class SystemConfig(Base):
    __tablename__ = "system_configs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(String, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

def import_template():
    yaml_path = r"e:\CursorData\VPNoldk\yaml.md"
    
    print(f"Reading {yaml_path}...")
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading YAML: {e}")
        return

    # Extract sections
    dns = data.get('dns', {})
    rules = data.get('rules', [])
    proxy_groups_raw = data.get('proxy-groups', [])
    
    # Process proxy groups
    new_groups = []
    standard_groups = ['节点选择', '自动选择', '漏网之鱼']
    
    # 1. Select Group (Manual)
    new_groups.append({
        'name': '节点选择',
        'type': 'select',
        'proxies': ['自动选择', 'DIRECT', '__NODES_PLACEHOLDER__']
    })
    
    # 2. Auto Select Group
    new_groups.append({
        'name': '自动选择',
        'type': 'url-test',
        'url': 'http://www.gstatic.com/generate_204',
        'interval': 300,
        'proxies': ['__NODES_PLACEHOLDER__']
    })
    
    # 3. Final Group
    new_groups.append({
        'name': '漏网之鱼',
        'type': 'select',
        'proxies': ['节点选择', 'DIRECT']
    })

    # 4. User's Specialized Groups
    for group in proxy_groups_raw:
        if isinstance(group, str): continue # Skip if malformed list
        name = group.get('name')
        if not name or name in standard_groups:
            continue
            
        # Simplified logic: specialized groups use Select Group + Auto + Direct
        new_group = {
            'name': name,
            'type': 'select',
            'proxies': ['节点选择', '自动选择', 'DIRECT']
        }
        new_groups.append(new_group)

    # Build Template Dict
    template = {
        'port': 7890,
        'socks-port': 7891,
        'allow-lan': True,
        'mode': 'Rule',
        'log-level': 'info',
        'external-controller': ':9090',
        'dns': dns,
        'proxies': ['__PROXIES_PLACEHOLDER__'],
        'proxy-groups': new_groups,
        'rules': rules
    }

    # Dump to YAML string
    yaml_str = yaml.dump(template, allow_unicode=True, sort_keys=False)
    
    # Replace placeholders
    yaml_str = yaml_str.replace('- __PROXIES_PLACEHOLDER__', '{proxies}')
    yaml_str = yaml_str.replace('- __NODES_PLACEHOLDER__', '{node_names}')
    yaml_str = yaml_str.replace("'__NODES_PLACEHOLDER__'", '{node_names}')

    # Save to DB
    db = SessionLocal()
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == "clash_template").first()
        if config:
            config.value = yaml_str
            config.description = f"Imported {len(rules)} rules from yaml.md"
        else:
            config = SystemConfig(key="clash_template", value=yaml_str, description=f"Imported {len(rules)} rules from yaml.md")
            db.add(config)
        db.commit()
        print("Successfully imported template to database.")
    except Exception as e:
        print(f"Error saving to DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_template()
