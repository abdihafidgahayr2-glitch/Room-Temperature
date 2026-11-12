from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
import logging

from fastapi import FastAPI, Request, HTTPException, status, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from schemas import (ReadingResponse, UserCreate, UserResponse, WindowCommand, WindowStatus,
                     SettingBase, SettingResponse)
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.orm import Session
import config
import models
import mqtt_client
from auth import get_current_user, hash_password, verify_password
from database import Base, engine, get_db

logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_client.start()
    yield
    mqtt_client.stop()


# /docs, /redoc and /openapi.json are turned off so no endpoint is open without a login
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(
    SessionMiddleware,
    secret_key=config.SESSION_SECRET,
    https_only=config.HTTPS_ONLY,  # cookie only sent over HTTPS on the real server
    same_site="strict",
    max_age=60 * 60 * 8,  # log out after 8 hours
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------- Pages ----------

@app.get("/login", include_in_schema=False, name="login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title": "Log in"})


@app.post("/login", include_in_schema=False)
def login(request: Request, username: Annotated[str, Form()], password: Annotated[str, Form()],
          db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.username == username))
    user = result.scalars().first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"title": "Log in", "error": "Wrong username or password"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(request.url_for("home"), status_code=status.HTTP_303_SEE_OTHER)


@app.post("/logout", include_in_schema=False, name="logout")
def logout(request: Request, user: Annotated[models.User, Depends(get_current_user)]):
    request.session.clear()
    return RedirectResponse(request.url_for("login"), status_code=status.HTTP_303_SEE_OTHER)


@app.get("/", include_in_schema=False, name="home")
@app.get("/dashboard", include_in_schema=False, name="dashboard")
def home(request: Request, user: Annotated[models.User, Depends(get_current_user)],
         db: Annotated[Session, Depends(get_db)]):
    open_at, close_at = mqtt_client.get_thresholds(db)
    result = db.execute(select(models.Reading).order_by(models.Reading.date_timestamp.desc()).limit(10))
    latest_readings = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "user": user,
            "latest_readings": latest_readings,
            "window_state": mqtt_client.get_window_state(db),
            "open_at": open_at,
            "close_at": close_at,
            "title": "Dashboard",
        },
    )


# ---------- API (every endpoint needs a login) ----------

@app.get("/api/sensor_readings", response_model=list[ReadingResponse])
def get_sensor_readings(user: Annotated[models.User, Depends(get_current_user)],
                        db: Annotated[Session, Depends(get_db)], hours: int = 24):
    hours = max(1, min(hours, 24 * 7))
    since = datetime.now(UTC) - timedelta(hours=hours)
    result = db.execute(select(models.Reading)
                        .where(models.Reading.date_timestamp >= since)
                        .order_by(models.Reading.date_timestamp))
    sensor_readings = result.scalars().all()
    return sensor_readings


@app.get("/api/sensor_reading/{sensor_reading_id}", response_model=ReadingResponse)
def get_sensor_reading(sensor_reading_id: int, user: Annotated[models.User, Depends(get_current_user)],
                       db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Reading).where(models.Reading.id == sensor_reading_id))
    reading = result.scalars().first()
    if reading:
        return reading
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor reading not found")


@app.get("/api/window", response_model=WindowStatus)
def get_window(user: Annotated[models.User, Depends(get_current_user)],
               db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.WindowEvent).order_by(models.WindowEvent.date_timestamp.desc()).limit(10))
    events = result.scalars().all()
    return {"state": mqtt_client.get_window_state(db), "events": events}


@app.post("/api/window", status_code=status.HTTP_202_ACCEPTED)
def control_window(command: WindowCommand, user: Annotated[models.User, Depends(get_current_user)]):
    if not mqtt_client.send_window_command(command.action, "manual"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Not connected to the MQTT broker")
    return {"sent": command.action}


@app.get("/api/settings", response_model=SettingResponse)
def get_settings(user: Annotated[models.User, Depends(get_current_user)],
                 db: Annotated[Session, Depends(get_db)]):
    open_at, close_at = mqtt_client.get_thresholds(db)
    return {"open_at": open_at, "close_at": close_at}


@app.put("/api/settings", response_model=SettingResponse)
def update_settings(setting: SettingBase, user: Annotated[models.User, Depends(get_current_user)],
                    db: Annotated[Session, Depends(get_db)]):
    if setting.close_at >= setting.open_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Close temperature must be lower than open temperature")
    result = db.execute(select(models.Setting).where(models.Setting.id == 1))
    existing_setting = result.scalars().first()
    if existing_setting:
        existing_setting.open_at = setting.open_at
        existing_setting.close_at = setting.close_at
    else:
        existing_setting = models.Setting(id=1, open_at=setting.open_at, close_at=setting.close_at)
        db.add(existing_setting)
    db.commit()
    db.refresh(existing_setting)
    return existing_setting


# Only a logged-in user can add another user (no public sign-up)
@app.post("/api/user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(new_user_data: UserCreate, user: Annotated[models.User, Depends(get_current_user)],
                db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.username == new_user_data.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    result = db.execute(select(models.User).where(models.User.email == new_user_data.email))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    new_user = models.User(
        username = new_user_data.username,
        email = new_user_data.email,
        password_hash = hash_password(new_user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/api/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int, user: Annotated[models.User, Depends(get_current_user)],
             db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    found_user = result.scalars().first()
    if found_user:
        return found_user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


# ---------- Error handlers ----------

@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again"
    )
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code = exception.status_code,
            content = {"detail": message}
        )
    # Not logged in on a page -> send them to the login page
    if exception.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(request.url_for("login"), status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code = exception.status_code,
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT,
            content = {"detail": exception.errors()}
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again",
        },
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
