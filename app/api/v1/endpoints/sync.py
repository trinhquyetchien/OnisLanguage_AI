from fastapi import APIRouter, Query, Depends

from app.api import deps
from app.db.models import User
from app.schemas.sync import SyncPullResponse, SyncPushRequest, SyncPushResponse, SyncSnapshotResponse
from app.services.sync_service import sync_service

router = APIRouter()


@router.post("/push", response_model=SyncPushResponse)
async def push_changes(
    request: SyncPushRequest,
    current_user: User = Depends(deps.get_current_user)
):
    return sync_service.push(request)


@router.get("/pull", response_model=SyncPullResponse)
async def pull_changes(
    current_user: User = Depends(deps.get_current_user), 
    since: int = Query(default=0, ge=0)
):
    return sync_service.pull(user_id=str(current_user.user_id), since=since)


@router.get("/snapshot", response_model=SyncSnapshotResponse)
async def snapshot(
    current_user: User = Depends(deps.get_current_user)
):
    return sync_service.snapshot(user_id=str(current_user.user_id))
