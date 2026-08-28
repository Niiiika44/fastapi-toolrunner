import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import RedirectResponse

from app.auth.dependencies import (
    effective_permissions,
    ensure_self_or_permission,
    get_current_admin,
    get_current_user,
    require,
)
from app.auth.enums import Permission
from app.auth.exceptions import NotEnoughPermissionsError
from app.core.config import get_settings
from app.core.openapi import error
from app.users.avatar_image import OUTPUT_MEDIA_TYPE
from app.users.dependencies import get_avatar_service, get_user_service
from app.users.models import User
from app.users.schemas import (
    AvatarLinkDomain,
    ChangeEmail,
    ChangePassword,
    CurrentUserResponse,
    RoleApproval,
    RoleAssignment,
    RoleRequest,
    UserPermissionResponse,
    UserResponse,
    UserUpdate,
)
from app.users.services import AvatarService, UserService

settings = get_settings()

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={401: error("Missing, expired or invalid token")},
)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get the current user"
)
def get_me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user).model_copy(
        update={"permissions": sorted(effective_permissions(current_user))}
    )


@router.get(
    "/role-requests",
    response_model=list[UserResponse],
    summary="List all user requests to change a role",
    description=(
        "Allowed for tsuperusers and for holders "
        "of the `user:update_any` permission."
    ),
    responses={
        403: error(
            "Allowed for the superuser or a holder of the user:update_any permission"
        )
    },
)
async def list_role_requests(
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require(Permission.USER_UPDATE_ANY)),
) -> list[UserResponse]:
    users = await user_service.list_role_requests()
    return [UserResponse.model_validate(user) for user in users]


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List all users",
    description="Requires the `user:read_any` permission.",
    responses={
        403: error("Requires the user:read_any permission"),
    },
)
async def get_all(
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require(Permission.USER_READ_ANY))
) -> list[UserResponse]:
    users = await user_service.show_all()
    return [UserResponse.model_validate(user) for user in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by id",
    responses={
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def get_user_by_id(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_user)
) -> UserResponse:
    user = await user_service.get_by_id(user_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user profile",
    description=(
        "Updates the given fields only. Allowed for the account owner "
        "and for holders of the `user:update_any` permission."
    ),
    responses={
        403: error(
            "Allowed for the account owner or a holder of the user:update_any permission"
        ),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def update_user(
    user_id: uuid.UUID,
    new_data: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    ensure_self_or_permission(current_user, user_id, Permission.USER_UPDATE_ANY)
    updated_user = await user_service.update(user_id, new_data)
    return UserResponse.model_validate(updated_user)


@router.post(
    "/{user_id}/change-password",
    response_model=UserResponse,
    summary="Change the account password",
    description="Allowed for the account owner only, superusers included.",
    responses={
        400: error("Old password is incorrect"),
        403: error("Only the account owner may change the password"),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def change_user_password(
    user_id: uuid.UUID,
    user_data: ChangePassword,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    if current_user.id != user_id:
        raise NotEnoughPermissionsError()
    user = await user_service.change_password(
        user_id=user_id,
        old_password=user_data.old_password,
        new_password=user_data.new_password
    )
    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/change-email",
    response_model=UserResponse,
    summary="Change the account email",
    description=(
        "Allowed for the account owner only, superusers included. "
        "Requires the current password. Only `@ispras.ru` addresses are accepted; "
        "the username is re-derived from the new address. "
        "Submitting the current email is a no-op and succeeds."
    ),
    responses={
        400: error("Password is incorrect, or the email domain is not allowed"),
        403: error("Only the account owner may change the email"),
        404: error("User not found"),
        409: error("Another user already uses this email"),
        422: error("Request validation failed"),
    },
)
async def change_user_email(
    user_id: uuid.UUID,
    user_data: ChangeEmail,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    if current_user.id != user_id:
        raise NotEnoughPermissionsError()
    user = await user_service.change_email(
        user_id=user_id,
        new_email=user_data.new_email,
        password=user_data.password
    )
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description=(
        "Allowed for the account owner and for holders "
        "of the `user:delete_any` permission."
    ),
    responses={
        403: error(
            "Allowed for the account owner or a holder of the user:delete_any permission"
        ),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def delete_user(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> None:
    ensure_self_or_permission(current_user, user_id, Permission.USER_DELETE_ANY)
    await user_service.delete(user_id)


@router.post(
    "/me/role-request",
    response_model=UserResponse,
    summary="Request a different role",
    responses={
        400: error("Role is already assigned"),
        422: error("Request validation failed"),
    },
)
async def send_change_role_request(
    user_data: RoleRequest,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    user = await user_service.request_role(current_user.id, user_data.job_title)
    return UserResponse.model_validate(user)


@router.delete(
    "/me/role-request",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw your own role request"
)
async def withdraw_change_role_request(
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
) -> None:
    await user_service.withdraw_role_request(current_user.id)


@router.post(
    "/{user_id}/role-request/approve",
    response_model=UserResponse,
    summary="Approve a pending role request",
    description=(
        "Allowed for superusers and for holders "
        "of the `user:update_any` permission."
    ),
    responses={
        403: error(
            "Allowed for the superuser or a holder of the user:update_any permission"
        ),
        404: error("User not found, or the user has no open role request"),
        409: error("User requested job title differs from approval request"),
        422: error("Request validation failed"),
    },
)
async def approve_role_request(
    user_id: uuid.UUID,
    user_data: RoleApproval,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require(Permission.USER_UPDATE_ANY)),
) -> UserResponse:
    user = await user_service.approve_role(user_id, user_data.expected_job_title)
    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/role-request/reject",
    response_model=UserResponse,
    summary="Reject a pending role request",
    description=(
        "Allowed for superusers and for holders "
        "of the `user:update_any` permission. Deletes requested job title, "
        "do not touches job title."
    ),
    responses={
        403: error(
            "Allowed for the superuser or a holder of the user:update_any permission"
        ),
        404: error("User not found, or the user has no open role request"),
        422: error("Request validation failed"),
    },
)
async def reject_role_request(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require(Permission.USER_UPDATE_ANY)),
) -> UserResponse:
    user = await user_service.reject_role(user_id)
    return UserResponse.model_validate(user)


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Assign a role directly",
    description=(
        "Allowed for superusers and for holders "
        "of the `user:update_any` permission."
    ),
    responses={
        403: error(
            "Allowed for the superuser or a holder of the user:update_any permission"
        ),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def change_user_role(
    user_id: uuid.UUID,
    user_data: RoleAssignment,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(require(Permission.USER_UPDATE_ANY)),
) -> UserResponse:
    user = await user_service.set_role(user_id, user_data.job_title)
    return UserResponse.model_validate(user)


@router.get(
    "/{user_id}/permissions",
    response_model=list[UserPermissionResponse],
    summary="List the individual permissions of a user",
    responses={
        403: error("Superuser privileges required"),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def list_user_permissions(
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_admin),
) -> list[UserPermissionResponse]:
    permissions = await user_service.list_permissions(user_id)
    return [UserPermissionResponse.model_validate(grant) for grant in permissions]


@router.post(
    "/{user_id}/permissions/{permission}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Grant a permission to a user",
    responses={
        403: error("Superuser privileges required"),
        404: error("User not found"),
        422: error("Unknown permission name, or request validation failed"),
    },
)
async def grant_user_permission(
    user_id: uuid.UUID,
    permission: Permission,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_admin),
) -> None:
    await user_service.grant_permission(user_id, permission)


@router.delete(
    "/{user_id}/permissions/{permission}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a permission from a user",
    responses={
        403: error("Superuser privileges required"),
        404: error("User not found"),
        422: error("Unknown permission name, or request validation failed"),
    },
)
async def revoke_user_permission(
    user_id: uuid.UUID,
    permission: Permission,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_admin),
) -> None:
    await user_service.revoke_permission(user_id, permission)


@router.get(
    "/{user_id}/avatar",
    response_model=None,
    response_class=Response,
    summary="Get the avatar of a user",
    responses={
        200: {
            "description": "Avatar image",
            "content": {"image/webp": {}},
        },
        302: {
            "description": "Redirect to a presigned storage link",
            "headers": {
                "Location": {
                    "description": "Presigned URL, expires after a configured TTL",
                    "schema": {"type": "string"},
                }
            },
        },
        404: error("The user does not exist, or has no avatar"),
        422: error("Request validation failed"),
    },
)
async def get_user_avatar(
    user_id: uuid.UUID,
    avatar_service: AvatarService = Depends(get_avatar_service),
) -> RedirectResponse | Response:
    avatar = await avatar_service.get_avatar(user_id)
    cache_control = f"public, max-age={settings.AVATAR_CACHE_SECONDS}"
    if isinstance(avatar, AvatarLinkDomain):
        return RedirectResponse(
            avatar.url,
            status_code=status.HTTP_302_FOUND,
            headers={"Cache-Control": cache_control},
        )
    return Response(
        content=avatar.content,
        media_type=OUTPUT_MEDIA_TYPE,
        headers={"Cache-Control": cache_control},
    )


@router.post(
    "/{user_id}/avatar",
    response_model=UserResponse,
    summary="Upload or replace an avatar",
    responses={
        400: error("The file is not a supported image, or cannot be decoded"),
        403: error(
            "Allowed for the account owner or a holder of the user:update_any permission"
        ),
        404: error("User not found"),
        413: error("The image is larger than the accepted limit"),
        422: error("Request validation failed"),
    },
)
async def upload_user_avatar(
    user_id: uuid.UUID,
    file: UploadFile = File(..., description="PNG, JPEG or WebP image"),
    avatar_service: AvatarService = Depends(get_avatar_service),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    ensure_self_or_permission(current_user, user_id, Permission.USER_UPDATE_ANY)
    user = await avatar_service.set_avatar(user_id, file)
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an avatar",
    description="Idempotent: removing an avatar that is not there succeeds and changes nothing.",
    responses={
        403: error(
            "Allowed for the account owner or a holder of the user:update_any permission"
        ),
        404: error("User not found"),
        422: error("Request validation failed"),
    },
)
async def delete_user_avatar(
    user_id: uuid.UUID,
    avatar_service: AvatarService = Depends(get_avatar_service),
    current_user: User = Depends(get_current_user),
) -> None:
    ensure_self_or_permission(current_user, user_id, Permission.USER_UPDATE_ANY)
    await avatar_service.delete_avatar(user_id)
