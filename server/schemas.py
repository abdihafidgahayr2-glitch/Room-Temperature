from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime
from typing import Literal


class ReadingBase(BaseModel):
    sensor: str = Field(min_length=1, max_length=20)
    content: float


class ReadingResponse(ReadingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date_timestamp: datetime


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: EmailStr = Field(max_length=320)


class UserCreate(UserBase):
    password: str = Field(min_length=10, max_length=72)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class WindowEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    state: str
    reason: str
    date_timestamp: datetime


class WindowStatus(BaseModel):
    state: str
    events: list[WindowEventResponse]


class WindowCommand(BaseModel):
    action: Literal["open", "close"]


class SettingBase(BaseModel):
    open_at: float = Field(ge=10, le=40)
    close_at: float = Field(ge=10, le=40)


class SettingResponse(SettingBase):
    model_config = ConfigDict(from_attributes=True)
