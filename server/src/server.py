# -*- coding: utf-8 -*-
"""
Agora Agent & Token Service — SwiftUI Quickstart Recipe

HTTP APIs:
- GET  /get_config     -> Generate connection config
- POST /startAgent     -> Start the agent
- POST /stopAgent      -> Stop agent
"""
import logging
import math
import os
import random
import time
from typing import Any, Dict, Literal, Optional
from urllib.parse import urlencode, urlparse
from dotenv import load_dotenv

# Load environment variables from .env.local or .env
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base_dir, '.env.local'), override=True)
load_dotenv(os.path.join(_base_dir, '.env'), override=True)

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from agora_agent.agentkit.token import generate_convo_ai_token
from agent import Agent

logger = logging.getLogger("uvicorn.error")


def _log_route_error(route: str, exc: Exception, **context) -> None:
    """Log route failures with safe request context and a traceback."""
    safe_context = {key: value for key, value in context.items() if value is not None}
    logger.exception(
        "Request failed route=%s context=%s error_type=%s error=%s",
        route,
        safe_context,
        type(exc).__name__,
        exc,
    )


def _to_http_error(exc: Exception) -> HTTPException:
    """Convert SDK exceptions to HTTP errors"""
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail=f"Internal error: {exc}")

try:
    agent = Agent()
except ValueError as e:
    logger.exception(
        "Failed to initialize Agent. Check environment variables: %s", e,
    )
    agent = None


# FastAPI provides configuration and lifecycle APIs for the iOS Agora client,
# plus the navigation-event handoff between the agent and that client.
app = FastAPI(
    title="Agora SwiftUI Quickstart Service",
    version="1.0.0",
    description="Agora Conversational AI — native iOS (SwiftUI) client quickstart",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()
# Single-process, one-pending-event-per-channel queue; GET consumes each event once.
_pending_navigation_events: Dict[str, Dict[str, Any]] = {}
_pending_map_link_events: Dict[str, Dict[str, Any]] = {}


# Request models
class StartAgentRequest(BaseModel):
    """Request body for POST /startAgent"""
    channelName: str
    rtcUid: int
    userUid: int
    parameters: Optional[Dict[str, Any]] = None


class StopAgentRequest(BaseModel):
    """Request body for POST /stopAgent"""
    agentId: str


class NavigationEventRequest(BaseModel):
    """Navigation destination event prepared for Agora RTM delivery."""
    type: Literal["navigation"]
    channel_name: str = Field(min_length=1, max_length=64)
    source: Optional[str] = Field(default=None, max_length=256)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    label: str = Field(min_length=1, max_length=256)


class MapLinkEventRequest(BaseModel):
    """A requested Google or Apple Maps link to display in the matching iOS call."""
    type: Literal["google_maps_link", "apple_maps_link"]
    channel_name: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=256)
    url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


def _is_allowed_google_maps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password or not valid_port:
        return False
    if host == "maps.app.goo.gl":
        return True
    if host == "maps.google.com":
        return True
    return host in {"google.com", "www.google.com"} and (
        parsed.path == "/maps" or parsed.path.startswith("/maps/")
    )


# API endpoints
def _generate_channel_name() -> str:
    return f"swiftui-quickstart-{int(time.time())}-{random.randint(1000, 9999)}"


@router.get("/get_config")
async def get_config(
    channel: Optional[str] = Query(default=None),
    uid: Optional[int] = Query(default=None),
):
    """Generate connection configuration"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        user_uid = random.randint(1000, 9999999) if uid is None or uid <= 0 else uid
        agent_uid = str(random.randint(10000000, 99999999))
        channel_name = channel or _generate_channel_name()

        app_id = os.getenv("AGORA_APP_ID")
        app_certificate = os.getenv("AGORA_APP_CERTIFICATE")

        token = generate_convo_ai_token(
            app_id=app_id,
            app_certificate=app_certificate,
            channel_name=channel_name,
            uid=user_uid,
            token_expire=3600,
        )

        config_data = {
            "app_id": app_id,
            "token": token,
            "uid": str(user_uid),
            "channel_name": channel_name,
            "agent_uid": agent_uid,
        }

        return {
            "code": 0,
            "data": config_data,
            "msg": "success",
        }
    except Exception as e:
        _log_route_error("/get_config", e, channel=channel, uid=uid)
        raise _to_http_error(e)


@router.post("/startAgent")
async def start_agent(request: StartAgentRequest):
    """Start the agent in a channel"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        output_audio_codec = None
        if request.parameters:
            output_audio_codec = request.parameters.get("output_audio_codec")

        result = await agent.start(
            channel_name=request.channelName,
            agent_uid=request.rtcUid,
            user_uid=request.userUid,
            output_audio_codec=output_audio_codec,
        )
        return {"code": 0, "msg": "success", "data": result}
    except Exception as e:
        _log_route_error(
            "/startAgent",
            e,
            channelName=request.channelName,
            rtcUid=request.rtcUid,
            userUid=request.userUid,
        )
        raise _to_http_error(e)


@router.post("/stopAgent")
async def stop_agent(request: StopAgentRequest):
    """Stop agent by ID"""
    if agent is None:
        raise HTTPException(
            status_code=500,
            detail="Service not properly configured. Please check environment variables.",
        )

    try:
        await agent.stop(request.agentId)
        return {"code": 0, "msg": "success"}
    except Exception as e:
        _log_route_error("/stopAgent", e, agentId=request.agentId)
        raise _to_http_error(e)


@router.post("/navigation-event", status_code=202)
async def navigation_event(request: NavigationEventRequest):
    """Validate and queue one navigation instruction for the matching iOS channel."""
    if not request.channel_name.strip():
        raise HTTPException(status_code=422, detail="channel_name cannot be blank")
    if not request.label.strip():
        raise HTTPException(status_code=422, detail="label cannot be blank")
    if not math.isfinite(request.latitude) or not math.isfinite(request.longitude):
        raise HTTPException(status_code=422, detail="coordinates must be finite numbers")

    event = request.dict(exclude={"source"})
    if request.source and request.source.strip():
        event["source"] = request.source.strip()
    _pending_navigation_events[request.channel_name] = event

    return {
        "code": 0,
        "msg": "queued",
        "data": event,
    }


@router.get("/navigation-event/{channel_name}")
async def get_navigation_event(channel_name: str):
    """Return and consume the channel's pending event so polling cannot replay it."""
    event = _pending_navigation_events.pop(channel_name, None)
    if event is None:
        raise HTTPException(status_code=404, detail="No pending navigation event")
    return {"code": 0, "msg": "success", "data": event}


@router.post("/map-link", status_code=202)
async def map_link_event(request: MapLinkEventRequest):
    """Validate and queue one explicitly requested map link for the iOS channel."""
    if not request.channel_name.strip() or not request.label.strip():
        raise HTTPException(status_code=422, detail="channel_name and label cannot be blank")

    if request.type == "google_maps_link":
        if not request.url or not _is_allowed_google_maps_url(request.url):
            raise HTTPException(status_code=422, detail="url must be an HTTPS Google Maps URL")
        event = request.dict(exclude_none=True)
    else:
        if request.latitude is None or request.longitude is None:
            raise HTTPException(status_code=422, detail="Apple Maps links require destination coordinates")
        event = request.dict(exclude={"url"}, exclude_none=True)
        event["url"] = "http://maps.apple.com/?" + urlencode(
            {
                "daddr": f"{request.latitude},{request.longitude}",
                "q": request.label,
            }
        )

    _pending_map_link_events[request.channel_name] = event
    # Keep the link out of the custom tool response returned to the LLM.
    return {"code": 0, "msg": "queued"}


@router.get("/map-link/{channel_name}")
async def get_map_link_event(channel_name: str):
    """Return and consume the channel's pending map link once."""
    event = _pending_map_link_events.pop(channel_name, None)
    if event is None:
        raise HTTPException(status_code=404, detail="No pending map link")
    return {"code": 0, "msg": "success", "data": event}


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
