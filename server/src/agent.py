"""
Agent — SwiftUI Quickstart Recipe

High-level API for managing an Agora Conversational AI Agent. RTM is enabled so
the native iOS client's ConversationalAIAPI toolkit can render the live
transcript (agent state and metrics ride the same data channel).

Pipeline:  DeepgramSTT(nova-3, en) → OpenAI (Agora-managed, keyless) → MiniMaxTTS

TourBuddy flow: user voice → Agora Conversational AI → Maps MCP; explicit
navigation → FastAPI event → iOS polling → Apple Maps.

OPENAI_API_KEY is optional — set it only if your account requires a BYO key.
"""
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from agora_agent import Area, AsyncAgora
from agora_agent.agentkit import Agent as AgoraAgent
from agora_agent.agentkit.vendors import OpenAI, DeepgramSTT, MiniMaxTTS

logger = logging.getLogger("uvicorn.error")


class Agent:
    """
    High-level wrapper for the Agora Conversational AI Agent.

    Uses the managed OpenAI vendor (Agora-managed, keyless) with a simple
    friendly prompt. Enables the RTM data channel, metrics, and error messages
    so the native iOS client can render the live transcript via the toolkit.
    """

    def __init__(self):
        self.app_id = os.getenv("AGORA_APP_ID")
        self.app_certificate = os.getenv("AGORA_APP_CERTIFICATE")
        self.greeting = os.getenv(
            "AGENT_GREETING",
            "Hi, I'm TourBuddy, your travel guide. Where would you like to explore today?",
        )

        # OpenAI is Agora-managed (keyless). OPENAI_API_KEY is optional.
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not self.app_id or not self.app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_APP_CERTIFICATE are required")

        self.client = AsyncAgora(
            area=Area.US,
            app_id=self.app_id,
            app_certificate=self.app_certificate,
        )

        # Track active sessions by agent_id
        self._sessions: Dict[str, Any] = {}

    async def start(
        self,
        channel_name: str,
        agent_uid: int,
        user_uid: int,
        output_audio_codec: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start the agent."""
        if not channel_name or not str(channel_name).strip():
            raise ValueError("channel_name is required and cannot be empty")
        if agent_uid <= 0:
            raise ValueError("agent_uid is required and cannot be empty")
        if user_uid <= 0:
            raise ValueError("user_uid is required and cannot be empty")

        # Maps Grounding Lite enriches answers: search_places resolves destinations
        # and compute_routes answers origin-to-destination route questions.
        maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        maps_mcp_servers = None
        if maps_api_key:
            maps_mcp_servers = [
                {
                    "name": "mapsGroundingLite",
                    "endpoint": "https://mapstools.googleapis.com/mcp",
                    "transport": "streamable_http",
                    "headers": {"X-Goog-Api-Key": maps_api_key},
                    "allowed_tools": [
                        "search_places",
                        "compute_routes",
                    ],
                }
            ]

        # This action is only for explicit navigate/open-in-Maps intent.
        navigation_tools = None
        navigation_event_url = os.getenv("NAVIGATION_EVENT_URL")
        if navigation_event_url:
            parsed_navigation_url = urlparse(navigation_event_url)
            if parsed_navigation_url.scheme != "https" or not parsed_navigation_url.netloc:
                raise ValueError("NAVIGATION_EVENT_URL must be an absolute HTTPS URL")

            navigation_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "publish_navigation_destination",
                        "description": (
                            "Required action for an explicit user command to navigate to, "
                            "be taken to, or open a destination in Maps. Resolve the "
                            "destination with search_places when needed, then call this "
                            "tool with its coordinates and label. Do not call it for "
                            "place questions, searches, distance or route information. "
                            "Do not substitute a Google Maps URL for this action."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "source": {
                                    "type": "string",
                                    "description": "Explicit starting location only. Use an empty string if the user did not provide one; never infer or assume a source.",
                                },
                                "latitude": {
                                    "type": "number",
                                    "description": "Resolved destination latitude.",
                                },
                                "longitude": {
                                    "type": "number",
                                    "description": "Resolved destination longitude.",
                                },
                                "label": {
                                    "type": "string",
                                    "description": "Human-readable destination name.",
                                },
                            },
                            "required": ["latitude", "longitude", "label", "source"],
                            "additionalProperties": False,
                        },
                    },
                    "server": {
                        "method": "POST",
                        "url": navigation_event_url,
                        "headers": {"Content-Type": "application/json"},
                        "body": {
                            "type": "navigation",
                            "channel_name": "{{template_variables.channel_name}}",
                            "latitude": "{{args.latitude}}",
                            "longitude": "{{args.longitude}}",
                            "label": "{{args.label}}",
                            "source": "{{args.source}}",
                        },
                        "timeout_ms": 10000,
                    },
                }
            ]

        system_prompt = (
            "You are TourBuddy AI, a friendly voice tour guide. Help users explore "
            "places, attractions, food, culture, and travel tips. Use search_places "
            "to find or identify places and compute_routes for route requests when "
            "both origin and destination are known. Ask for missing or ambiguous "
            "locations. Keep replies to one or two sentences and include source "
            "attribution when available."
        )
        if navigation_tools:
            system_prompt += (
                " Treat a direct command to navigate to, take the user to, or open a "
                "destination in Maps as an action request. For those requests, resolve "
                "the destination with search_places if its coordinates are not already "
                "known. If the user explicitly provides a starting location, pass it as "
                "source; otherwise pass an empty string. Never infer or assume a source. "
                "Then you MUST call publish_navigation_destination with the resolved "
                "destination latitude, longitude, and label. A route calculation or a "
                "Google Maps URL is not a substitute for this call. For ordinary place "
                "questions, place searches, distance questions, and requests for route "
                "information, answer normally with the relevant Maps tools and do not "
                "call the navigation action unless the user explicitly asks to navigate "
                "or open the destination in Maps. After the action succeeds, respond "
                "briefly and naturally; never mention the tool or provide a Maps URL."
            )

        llm = OpenAI(
            api_key=self.openai_api_key,
            model=self.openai_model,
            mcp_servers=maps_mcp_servers,
            tools=navigation_tools,
            template_variables=(
                {"channel_name": channel_name} if navigation_tools else None
            ),
            system_messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ],
            greeting_message=self.greeting,
            temperature=0.7,
        )

        stt = DeepgramSTT(model="nova-3", language="en")
        tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")

        parameters = {
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        }
        if isinstance(output_audio_codec, str) and output_audio_codec.strip():
            parameters["output_audio_codec"] = output_audio_codec.strip()

        agora_agent = AgoraAgent(
            client=self.client,
            greeting=self.greeting,
            failure_message="Please wait a moment.",
            max_history=50,
            turn_detection={
                "config": {
                    "speech_threshold": 0.5,
                    "start_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "interrupt_duration_ms": 160,
                            "prefix_padding_ms": 300,
                        },
                    },
                    "end_of_speech": {
                        "mode": "vad",
                        "vad_config": {
                            "silence_duration_ms": 480,
                        },
                    },
                },
            },
            advanced_features={"enable_rtm": True},
            parameters=parameters,
        )

        agora_agent = (
            agora_agent
            .with_stt(stt)
            .with_llm(llm)
            .with_tts(tts)
        )
        if maps_mcp_servers or navigation_tools:
            agora_agent = agora_agent.with_tools(True)

        session = agora_agent.create_async_session(
            channel=channel_name,
            agent_uid=str(agent_uid),
            remote_uids=[str(user_uid)],
            enable_string_uid=False,
            idle_timeout=30,
            expires_in=3600,
        )

        logger.info(
            "Starting agent channel=%s agent_uid=%s user_uid=%s",
            channel_name,
            agent_uid,
            user_uid,
        )

        try:
            agent_id = await session.start()
        except Exception:
            logger.exception(
                "Failed to start agent channel=%s agent_uid=%s user_uid=%s",
                channel_name,
                agent_uid,
                user_uid,
            )
            raise

        # Save session for later stop
        self._sessions[agent_id] = session

        logger.info(
            "Started agent agent_id=%s channel=%s",
            agent_id,
            channel_name,
        )

        return {
            "agent_id": agent_id,
            "channel_name": channel_name,
            "status": "started",
        }

    async def stop(self, agent_id: str) -> None:
        """Stop a running agent. Falls back to the stateless client path."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")

        session = self._sessions.pop(agent_id, None)
        if session:
            try:
                await session.stop()
                logger.info("Stopped agent from active session agent_id=%s", agent_id)
                return
            except Exception:
                logger.warning(
                    "Failed to stop agent from active session; falling back agent_id=%s",
                    agent_id,
                    exc_info=True,
                )

        logger.info("Stopping agent through client.stop_agent agent_id=%s", agent_id)
        await self.client.stop_agent(agent_id)
