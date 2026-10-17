from fastapi import APIRouter

from app.auth.deps import CurrentUser
from app.schemas.response import ApiResponse, success
from app.schemas.user import UserRead

router = APIRouter(tags=["account"])


@router.get("/me", response_model=ApiResponse[UserRead])
async def read_me(user: CurrentUser) -> ApiResponse[UserRead]:
    return success(UserRead.model_validate(user))
