"""
Admin API Router
用于管理后台的 API 接口 (节点管理、系统配置等)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.routers.auth import get_current_user
from app.models import User, Server, SystemConfig

router = APIRouter(prefix="/admin", tags=["Admin"])

# === Pydantic Models ===

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    type: Optional[str] = None
    location: Optional[str] = None
    flag: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    tags: Optional[str] = None
    rate_multiplier: Optional[float] = None

class ServerCreate(ServerUpdate):
    name: str
    host: str
    port: int

class ServerResponse(ServerCreate):
    id: int

    class Config:
        from_attributes = True

class ConfigUpdate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class ConfigResponse(ConfigUpdate):
    id: int
    updated_at: Optional[str] = None 

    class Config:
        from_attributes = True

# === Dependencies ===

from app.auth import get_current_admin

# === Endpoints ===

# --- Server / Node Management ---

@router.get("/nodes", response_model=List[ServerResponse])
def get_nodes(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """获取所有节点列表"""
    return db.query(Server).order_by(Server.sort_order).all()

@router.post("/nodes", response_model=ServerResponse)
def create_node(node: ServerCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """创建一个新节点"""
    db_node = Server(**node.dict())
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return db_node

@router.put("/nodes/{node_id}", response_model=ServerResponse)
def update_node(node_id: int, node_update: ServerUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """更新节点信息"""
    db_node = db.query(Server).filter(Server.id == node_id).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    update_data = node_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_node, key, value)
    
    db.commit()
    db.refresh(db_node)
    return db_node

@router.delete("/nodes/{node_id}")
def delete_node(node_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """删除节点"""
    db_node = db.query(Server).filter(Server.id == node_id).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    db.delete(db_node)
    db.commit()
    return {"message": "Node deleted"}

# --- System Config Management ---

@router.get("/config/{key}", response_model=ConfigResponse)
def get_config(key: str, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """获取特定配置"""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        # Return empty/default if not found
        return {"id": 0, "key": key, "value": "", "description": "Auto-generated"}
    return config

@router.post("/config", response_model=ConfigResponse)
def update_config(config_data: ConfigUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """更新或创建配置"""
    config = db.query(SystemConfig).filter(SystemConfig.key == config_data.key).first()
    if config:
        config.value = config_data.value
        if config_data.description:
            config.description = config_data.description
    else:
        config = SystemConfig(
            key=config_data.key,
            value=config_data.value,
            description=config_data.description
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    return config
