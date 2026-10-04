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
        map_link_tools = None
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

            navigation_path = parsed_navigation_url.path.rstrip("/")
            if navigation_path.endswith("/navigation-event"):
                link_path = f"{navigation_path[:-len('navigation-event')]}map-link"
            else:
                link_path = f"{navigation_path}/map-link"
            map_link_event_url = parsed_navigation_url._replace(path=link_path).geturl()
            map_link_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "publish_google_maps_link",
                        "description": (
                            "For every explicit request for a Google Maps link or URL, "
                            "or to show/view a specific place on Google Maps (without "
                            "requesting directions or navigation), first call search_places "
                            "to resolve that place, then MUST call this tool with its exact "
                            "googleMapsLinks.placeUrl and place label. Do not answer with "
                            "text instead of calling this tool. Never invent, construct, "
                            "alter, or use another URL. If you offer a Google Maps URL "
                            "after an ordinary place answer, call this tool immediately "
                            "before saying the link is available; never ask whether the "
                            "user wants the URL and stop. Do not call for ordinary place "
                            "questions unless you offer a link, or for navigation requests."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "The exact googleMapsLinks.placeUrl returned by search_places.",
                                },
                                "label": {
                                    "type": "string",
                                    "description": "Human-readable name of the place.",
                                },
                            },
                            "required": ["url", "label"],
                            "additionalProperties": False,
                        },
                    },
                    "server": {
                        "method": "POST",
                        "url": map_link_event_url,
                        "headers": {"Content-Type": "application/json"},
                        "body": {
                            "type": "google_maps_link",
                            "channel_name": "{{template_variables.channel_name}}",
                            "url": "{{args.url}}",
                            "label": "{{args.label}}",
                        },
                        "timeout_ms": 10000,
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "publish_apple_maps_link",
                        "description": (
                            "For an explicit request for an Apple Maps link, publish the "
                            "resolved destination to the app. Do not call this for a request "
                            "to navigate or open Maps; those use the navigation action."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "latitude": {
                                    "type": "number",
                                    "description": "Resolved destination latitude from search_places.",
                                },
                                "longitude": {
                                    "type": "number",
                                    "description": "Resolved destination longitude from search_places.",
                                },
                                "label": {
                                    "type": "string",
                                    "description": "Human-readable destination name.",
                                },
                            },
                            "required": ["latitude", "longitude", "label"],
                            "additionalProperties": False,
                        },
                    },
                    "server": {
                        "method": "POST",
                        "url": map_link_event_url,
                        "headers": {"Content-Type": "application/json"},
                        "body": {
                            "type": "apple_maps_link",
                            "channel_name": "{{template_variables.channel_name}}",
                            "latitude": "{{args.latitude}}",
                            "longitude": "{{args.longitude}}",
                            "label": "{{args.label}}",
                        },
                        "timeout_ms": 10000,
                    },
                },
            ]

        custom_tools = (navigation_tools or []) + (map_link_tools or [])

        system_prompt = (
            "You are TourBuddy, a friendly, helpful AI voice companion. Users may "
            "naturally address you as TourBuddy. Answer general questions naturally, "
            "not only travel questions. Use search_places for geographic information "
            "and place discovery, and compute_routes for route questions when both "
            "origin and destination are known. Ask for missing or ambiguous locations. "
            "For ordinary place, restaurant, and route requests that do not explicitly "
            "ask for a map link, summarize useful results in natural language; do not "
            "repeat, display, or speak URLs from Maps tool results, and do not publish a "
            "map-link event. This restriction does not apply to explicit map-link requests. "
            "For ordinary place questions, do not volunteer to provide a Google Maps URL. "
            "If you do offer one, first call publish_google_maps_link with the exact "
            "googleMapsLinks.placeUrl and place label, then briefly say it was added; "
            "never ask whether the user wants the URL before publishing it. "
            "If the user explicitly asks for a map URL or link, provide a legitimate "
            "URL only if it is available from a Google Maps tool result or trusted "
            "context; never invent one. If a separate text/link display is available, "
            "provide it there; never include or read a long raw URL in spoken output. "
            "If no separate text/link display is available, do not include the URL. "
            "After providing the link, ask, 'Would you like me to navigate you there?' "
            "only if the user has not already explicitly asked to navigate. Only navigate "
            "when the user explicitly requests it; for explicit navigation requests, "
            "call the navigation tool without asking for confirmation. Answer place "
            "questions normally without triggering navigation. Keep "
            "spoken replies concise and include source attribution when available."
        )
        if map_link_tools:
            system_prompt += (
                "An explicit request for a Google Maps link, Google Maps URL, or to "
                "show/view a specific place on Google Maps (without asking for directions "
                "or navigation) overrides the ordinary-search URL restriction. First "
                "resolve the requested place with search_places, including natural-language "
                "references such as 'the first restaurant' when needed. Then you MUST call "
                "publish_google_maps_link with that place's exact googleMapsLinks.placeUrl "
                "and label. Do not answer the link request with text instead of calling the "
                "tool, and do not invent, construct, or alter a URL. After the tool succeeds, "
                "give one short natural spoken response such as 'I've added the Google Maps "
                "link.' Never include the raw URL in assistant response text or speech; the "
                "separate map-link event is the only place the URL should be exposed. Do not "
                "claim the link was added unless the tool succeeds. For an Apple Maps link, "
                "resolve the place "
                "with search_places and call publish_apple_maps_link. The event displays the "
                "URL in the app. Never put a URL, Markdown link syntax, or the placeholder "
                "'[here]' in your spoken response. A link request is not a request to "
                "navigate: do not call publish_navigation_destination. Do not publish links "
                "for ordinary place questions or searches. Offer navigation only if the user "
                "has not already explicitly asked to navigate."
            )
        if navigation_tools:
            system_prompt += (
                " Treat only an explicit request to navigate to, go to, take the user "
                "to, or open a "
                "destination in Maps as an action request. For those requests, resolve "
                "the destination with search_places if its coordinates are not already "
                "known. If the user explicitly provides a starting location, pass it as "
                "source; otherwise pass an empty string. Never infer or assume a source. "
                "Then you MUST call publish_navigation_destination with the resolved "
                "destination latitude, longitude, and label. A route calculation or a "
                "Google Maps URL is not a substitute for this call. For ordinary place "
                "questions, place searches, distance questions, and requests for route "
                "information, answer normally with the relevant Maps tools and do not "
                "call the navigation action unless the user explicitly asks to navigate, "
                "go to, or open the destination in Maps. After the action succeeds, respond "
                "briefly and naturally without mentioning the tool."
            )

        llm = OpenAI(
            api_key=self.openai_api_key,
            model=self.openai_model,
            mcp_servers=maps_mcp_servers,
            tools=custom_tools or None,
            template_variables=(
                {"channel_name": channel_name} if custom_tools else None
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
