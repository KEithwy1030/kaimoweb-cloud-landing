from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import ApiResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/wallet", tags=["钱包"])

@router.post("/recharge", response_model=ApiResponse, summary="模拟充值")
def recharge_balance(
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    模拟充值余额（测试用）
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="金额必须大于0")
    
    current_user.balance = float(current_user.balance or 0) + amount
    db.commit()
    db.refresh(current_user)
    
    return ApiResponse(
        code=0,
        message=f"已成功充值 ¥{amount:.2f}",
        data={"balance": float(current_user.balance)}
    )
