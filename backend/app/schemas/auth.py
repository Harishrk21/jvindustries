from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=50, description="User code / User ID")
    password: str = Field(..., min_length=1, max_length=128)


class RoleOut(BaseModel):
    code: str
    name: str


class UserOut(BaseModel):
    id: str
    user_code: str
    full_name: str
    roles: list[str]
    permissions: list[str]
    must_change_password: bool = False

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class DeviceRegisterRequest(BaseModel):
    device_uid: str = Field(..., min_length=3, max_length=128)
    device_name: str = Field(default="", max_length=150)
    platform: str = Field(default="android", max_length=50)
    app_version: str = Field(default="", max_length=50)


class DeviceOut(BaseModel):
    id: str
    device_uid: str
    device_name: str
    platform: str
    app_version: str
    is_active: bool

    model_config = {"from_attributes": True}
