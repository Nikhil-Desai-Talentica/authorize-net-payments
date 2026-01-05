"""Transaction endpoints"""
from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_current_user

router = APIRouter()


@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get transaction by ID - placeholder"""
    # TODO: Implement transaction retrieval
    return {"message": "Get transaction endpoint - to be implemented"}


@router.get("/transactions")
async def list_transactions(
    current_user: dict = Depends(get_current_user),
):
    """List transactions - placeholder"""
    # TODO: Implement transaction listing
    return {"message": "List transactions endpoint - to be implemented"}

