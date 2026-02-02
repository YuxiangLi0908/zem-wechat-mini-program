from fastapi import APIRouter

from app.data_models.heartbeat import HeartbeatResult

router = APIRouter()


@router.get("/heartbeat", response_model=HeartbeatResult, name="heartbeat")
async def get_heartbeat() -> HeartbeatResult:
    """
    Get status of the service

    Returns:
        HeartbeatResult: bool status of the service
    """
    return HeartbeatResult(is_alive=True)
