import os
import json
import logging
from typing import Optional
import asyncio
import re
from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
HA_BASE_URL = os.environ.get("HA_BASE_URL", "http://homeassistant:8123")
HTTP_TIMEOUT = 30.0

# Read version from config.yaml
def get_version() -> str:
    """Reads the version from config.yaml file."""
    try:
        # Try relative path from app folder first
        config_path = Path(__file__).parent.parent / "config.yaml"
        if not config_path.exists():
            # Try in container root
            config_path = Path("/config.yaml")
        
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                return config.get("version", "unknown")
        else:
            logger.warning(f"config.yaml not found in {config_path}")
            return "unknown"
    except Exception as e:
        logger.warning(f"Unable to read version from config.yaml: {e}")
        return "unknown"

VERSION = get_version()

# FastAPI app
app = FastAPI(title="MCP Server for Home Assistant")

# HTTP client for Home Assistant API
http_client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)


# Global request logger (before middleware)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"🔵 RAW REQUEST: {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    response = await call_next(request)
    logger.info(f"🟢 RESPONSE: {response.status_code}")
    return response


# Auth middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log every incoming request
        logger.info(f"=== Incoming Request ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"Path: {request.url.path}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Skip auth for health endpoint
        if request.url.path.endswith("/health"):
            logger.info(f"Health check endpoint - skipping auth")
            return await call_next(request)
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            logger.warning(f"Missing Authorization header")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Missing or invalid Authorization header"}
            )
        
        logger.info(f"Authorization header present: {auth_header[:20]}...")
        
        if not auth_header.startswith("Bearer "):
            logger.warning(f"Invalid Authorization header format (doesn't start with 'Bearer ')")
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Missing or invalid Authorization header"}
            )
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        logger.info(f"Token extracted, length: {len(token)}, starts with: {token[:10]}...")
        
        # Validate token with Home Assistant
        try:
            logger.info(f"Validating token with Home Assistant at {HA_BASE_URL}/api/")
            response = await http_client.get(
                f"{HA_BASE_URL}/api/",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            logger.info(f"HA validation response: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"Token validation failed with status {response.status_code}")
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized", "message": "Invalid Home Assistant token"}
                )
            
            # Token is valid, attach to request state for later use
            request.state.ha_token = token
            logger.info("Token validated successfully")
            
        except httpx.RequestError as e:
            logger.error(f"Failed to validate token with Home Assistant: {e}")
            return JSONResponse(
                status_code=503,
                content={"error": "Service Unavailable", "message": "Cannot reach Home Assistant"}
            )
        
        return await call_next(request)


# Add middleware
app.add_middleware(AuthMiddleware)


# Health endpoint
@app.get("/health")
@app.get("/mcp/health")
async def health():
    return {"status": "healthy", "service": "mcp-ha-server"}


# SSE endpoint for MCP Streamable HTTP
@app.get("/mcp")
@app.get("/mcp/")
async def mcp_sse_endpoint(request: Request):
    """Server-Sent Events endpoint for MCP Streamable HTTP transport."""
    logger.info("SSE endpoint called for MCP connection")
    
    async def event_generator():
        try:
            # Send initial endpoint info as SSE
            endpoint_data = {
                "jsonrpc": "2.0",
                "method": "endpoint",
                "params": {
                    "endpoint": "/mcp/messages"
                }
            }
            yield f"data: {json.dumps(endpoint_data)}\n\n"
            
            # Keep connection alive
            while True:
                await asyncio.sleep(30)
                yield f": keepalive\n\n"
                
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Helper function to call Home Assistant API
async def call_ha_api(
    method: str,
    path: str,
    token: str,
    data: Optional[dict] = None
) -> dict:
    """Call Home Assistant REST API and return response."""
    url = f"{HA_BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        if method == "GET":
            response = await http_client.get(url, headers=headers)
        elif method == "POST":
            response = await http_client.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        # Prefer JSON; fallback to text for endpoints like /api/template
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.json()
        # Try JSON anyway; if it fails, return raw text
        try:
            return response.json()
        except Exception:
            return response.text
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HA API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Home Assistant API error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error calling HA API: {e}")
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Home Assistant"
        )


# MCP JSON-RPC 2.0 endpoint
@app.post("/")
@app.post("/messages")
@app.post("/mcp")
@app.post("/mcp/")
@app.post("/mcp/messages")
async def handle_messages(request: Request):
    """Handle MCP JSON-RPC 2.0 messages."""
    token = request.state.ha_token
    body = await request.json()
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    logger.info(f"MCP Request: method={method}, id={request_id}, params_keys={list(params.keys()) if params else []}")
    
    try:
        # Initialize
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "home-assistant-mcp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        
        # Initialized notification
        elif method == "notifications/initialized":
            # This is a notification, no response needed
            logger.info("Client initialized notification received")
            return JSONResponse(status_code=200, content={})
        
        # List tools
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "ha_list_states",
                        "description": "Get all entity states from Home Assistant (use sparingly, returns large payload)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    {
                        "name": "ha_list_states_filtered",
                        "description": "Get filtered entity states by domain and/or state (more efficient than ha_list_states)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": "Filter by domain (e.g., 'light', 'switch', 'sensor')"
                                },
                                "state": {
                                    "type": "string",
                                    "description": "Filter by state (e.g., 'on', 'off', 'unavailable')"
                                }
                            },
                            "required": []
                        }
                    },
                    {
                        "name": "ha_get_state",
                        "description": "Get state of a specific entity from Home Assistant",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "entity_id": {
                                    "type": "string",
                                    "description": "Entity ID (e.g., light.living_room)"
                                }
                            },
                            "required": ["entity_id"]
                        }
                    },
                    {
                        "name": "ha_get_history",
                        "description": "Get state history for one or more entities",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "entity_id": {
                                    "type": "string",
                                    "description": "Entity ID (e.g., sensor.temperature)"
                                },
                                "start_time": {
                                    "type": "string",
                                    "description": "Start time in ISO 8601 format (e.g., 2024-01-01T00:00:00+00:00)"
                                },
                                "end_time": {
                                    "type": "string",
                                    "description": "End time in ISO 8601 format (optional)"
                                }
                            },
                            "required": ["entity_id"]
                        }
                    },
                    {
                        "name": "ha_render_template",
                        "description": "Render a Jinja2 template to query or manipulate data from Home Assistant",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "template": {
                                    "type": "string",
                                    "description": "Jinja2 template string (e.g., '{{ states.light | list }}')"
                                }
                            },
                            "required": ["template"]
                        }
                    },
                    {
                        "name": "ha_list_services",
                        "description": "Get all available services from Home Assistant",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    {
                        "name": "ha_call_service",
                        "description": "Call a Home Assistant service",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": "Service domain (e.g., light, switch)"
                                },
                                "service": {
                                    "type": "string",
                                    "description": "Service name (e.g., turn_on)"
                                },
                                "data": {
                                    "type": "object",
                                    "description": "Service call data"
                                }
                            },
                            "required": ["domain", "service"]
                        }
                    },
                    {
                        "name": "ha_get_config",
                        "description": "Get Home Assistant configuration information",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    },
                    {
                        "name": "ha_get_logbook",
                        "description": "Get logbook entries (events and state changes)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "entity_id": {
                                    "type": "string",
                                    "description": "Filter by entity ID (optional)"
                                },
                                "start_time": {
                                    "type": "string",
                                    "description": "Start time in ISO 8601 format"
                                },
                                "end_time": {
                                    "type": "string",
                                    "description": "End time in ISO 8601 format (optional)"
                                }
                            },
                            "required": []
                        }
                    },
                    {
                        "name": "ha_fire_event",
                        "description": "Fire an event on the Home Assistant event bus",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "event_type": {
                                    "type": "string",
                                    "description": "Event type to fire"
                                },
                                "event_data": {
                                    "type": "object",
                                    "description": "Event data (optional)"
                                }
                            },
                            "required": ["event_type"]
                        }
                    }
                ]
            }
        
        # Call tool
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"Tool called: {tool_name}, arguments_keys={list(arguments.keys())}")
            
            # Wrap tool execution to catch HA API errors and return 200 with structured error
            try:
                tool_result = await execute_tool(tool_name, arguments, token)
            except HTTPException as e:
                # Return 200 with structured error info for agent consumption
                status_code = e.status_code
                detail = str(e.detail)
                tool_result = {
                    "error": "ha_api_error",
                    "status_code": status_code,
                    "message": detail,
                    "suggestion": get_error_suggestion(status_code, detail, tool_name, arguments),
                    "tool": tool_name,
                    "arguments": arguments
                }
            
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(tool_result, indent=2)
                    }
                ]
            }
        
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": request_id
                }
            )
        
        logger.info(f"MCP Response: method={method}, id={request_id}, result_keys={list(result.keys())}")
        return JSONResponse(
            status_code=200,
            content={
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
        )
    
    except Exception as e:
        logger.error(f"Error handling MCP request: method={method}, error={e}", exc_info=True)


def get_error_suggestion(status_code: int, detail: str, tool_name: str, arguments: dict) -> str:
    """
    Generate context-aware error suggestions based on status code, error message,
    tool name, and arguments.
    """
    if status_code == 404:
        if tool_name == "ha_get_state":
            entity_id = arguments.get("entity_id", "")
            return (
                f"Entity '{entity_id}' not found. Check the entity_id spelling or use "
                "ha_list_states to see all available entities."
            )
        elif tool_name == "ha_call_service":
            domain = arguments.get("domain", "")
            service = arguments.get("service", "")
            return (
                f"Service '{domain}.{service}' not found. Use ha_list_services to see available services, "
                "or verify the domain and service names are correct."
            )
        else:
            return "Resource not found. Verify the requested resource exists in Home Assistant."
    
    elif status_code == 400:
        if "entity" in detail.lower() or "entity_id" in detail.lower():
            return "Invalid entity_id provided. Check entity name format (domain.name) and spelling."
        else:
            return "Bad request. Check that all required parameters are provided with valid values."
    
    elif status_code == 401 or status_code == 403:
        return "Authentication or authorization failed. Check your Home Assistant access token."
    
    elif status_code == 500:
        # Enhanced 500 error handling with service-specific suggestions
        if tool_name == "ha_call_service":
            domain = arguments.get("domain", "")
            service = arguments.get("service", "")
            service_data = arguments.get("data", {})
            
            # Media player specific suggestions
            if domain == "media_player" and service == "play_media":
                entity_id = service_data.get("entity_id", "")
                media_id = service_data.get("media_content_id", "")
                media_type = service_data.get("media_content_type", "")
                
                # Enhanced suggestions for Spotify on Sonos
                if "sonos" in entity_id.lower() and "spotify" in str(media_id).lower():
                    return (
                        f"Error playing Spotify on Sonos '{entity_id}'. "
                        "Common causes: (1) Spotify account not linked to Sonos in Home Assistant, "
                        "(2) Invalid Spotify URI format, (3) Sonos device offline. "
                        "Try: (1) Check HA logs for Spotify authentication errors, "
                        "(2) Verify Spotify URI format (spotify:playlist:ID, spotify:track:ID, etc.), "
                        "(3) Ensure Sonos is powered on and connected, "
                        "(4) Try using 'enqueue' parameter (replace/add/next/play)."
                    )
                else:
                    return (
                        f"Error calling media_player.play_media on '{entity_id}'. "
                        "Common causes: (1) Device is offline or unavailable, (2) Invalid media_content_id format, "
                        "(3) Media source not authenticated (e.g., Spotify). Check that the media_content_id is correct "
                        "and the device is online. For Spotify, ensure media_content_id uses lowercase 'spotify:' prefix."
                    )
            else:
                return f"Service {domain}.{service} failed on Home Assistant. Check service parameters and Home Assistant logs."
        else:
            return "Home Assistant API returned 500 Internal Server Error. Check Home Assistant logs for details."
    
    else:
        return f"Home Assistant API returned {status_code}. Check Home Assistant logs for details."


async def execute_tool(tool_name: str, arguments: dict, token: str):
    """Execute a tool and return the result."""
    if tool_name == "ha_list_states":
        tool_result = await call_ha_api("GET", "/api/states", token)
    
    elif tool_name == "ha_list_states_filtered":
        # Get all states and filter locally
        all_states = await call_ha_api("GET", "/api/states", token)
        domain_filter = arguments.get("domain")
        state_filter = arguments.get("state")
        
        filtered_states = all_states
        if domain_filter:
            filtered_states = [s for s in filtered_states if s.get("entity_id", "").startswith(f"{domain_filter}.")]
        if state_filter:
            filtered_states = [s for s in filtered_states if s.get("state") == state_filter]
        
        tool_result = filtered_states
    
    elif tool_name == "ha_get_state":
        entity_id = arguments.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id is required")
        tool_result = await call_ha_api("GET", f"/api/states/{entity_id}", token)
    
    elif tool_name == "ha_get_history":
        entity_id = arguments.get("entity_id")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        
        if not entity_id:
            raise ValueError("entity_id is required")
        
        # Build query parameters
        params = []
        if start_time:
            params.append(f"filter_entity_id={entity_id}")
        
        # Construct URL
        timestamp = start_time if start_time else ""
        url_path = f"/api/history/period/{timestamp}"
        if params:
            url_path += "?" + "&".join(params)
        
        tool_result = await call_ha_api("GET", url_path, token)
    
    elif tool_name == "ha_render_template":
        template = arguments.get("template")
        if not template:
            raise ValueError("template is required")
        
        try:
            tool_result = await call_ha_api("POST", "/api/template", token, {"template": template})
        except HTTPException as e:
            # Enhance error message for unsupported filters (e.g., 'avg')
            detail = getattr(e, "detail", str(e))
            msg = str(detail)
            m = re.search(r"No filter named '([A-Za-z0-9_]+)'", msg)
            suggestion = None
            if m:
                bad_filter = m.group(1)
                if bad_filter.lower() == "avg":
                    suggestion = (
                        "Home Assistant does not provide an 'avg' filter. "
                        "Use 'average' (numeric function/filter) instead, or compute it as "
                        "(sum(list) / count(list)) after mapping to numbers."
                    )
                else:
                    suggestion = (
                        f"Filter '{bad_filter}' is not available. Refer to HA templating docs "
                        "for supported filters like average, median, min, max, sum, count, map, selectattr, etc."
                    )
            # Suggest handling for float invalid input (e.g., 'unknown')
            if not suggestion:
                m2 = re.search(r"float got invalid input '([^']+)'[^\"]*no default was specified", msg)
                if m2:
                    bad_val = m2.group(1)
                    suggestion = (
                        "The 'float' filter failed due to non-numeric values (e.g., '"
                        + bad_val +
                        "'). Use one of: map('float', default=0), or filter out non-numerics "
                        "with select('is_number') before converting, or use average with a default: "
                        "list | average(0)."
                    )
            # Return 200 with explanation instead of raising 400 (agent-friendly)
            tool_result = {
                "error": "template_render_error",
                "message": msg,
                "suggestion": suggestion or "See HA templating docs for supported filters and numeric handling.",
                "docs_url": "https://www.home-assistant.io/docs/configuration/templating/",
                "template": template
            }
    
    elif tool_name == "ha_list_services":
        tool_result = await call_ha_api("GET", "/api/services", token)
    
    elif tool_name == "ha_call_service":
        domain = arguments.get("domain")
        service = arguments.get("service")
        data = arguments.get("data") or {}
        if not domain or not service:
            raise ValueError("domain and service are required")

        # Log service data for debugging
        logger.info(f"Calling service {domain}/{service} with data: {json.dumps(data, indent=2)}")

        # Handle media_player.play_media for Sonos + Spotify
        if domain == "media_player" and service == "play_media":
            entity_id = data.get("entity_id", "")
            
            # Check if using old format (not supported for Sonos)
            if "sonos" in entity_id.lower() and "media_content_id" in data:
                media_id = data.get("media_content_id")
                media_type = data.get("media_content_type")
                
                # Check if it's Spotify content
                is_spotify = False
                if isinstance(media_id, str):
                    is_spotify = (
                        media_id.lower().startswith("spotify:") or 
                        media_id.lower().startswith("spotify://")
                    )
                
                if is_spotify:
                    logger.warning(f"Old format detected for Sonos+Spotify playback")
                    return {
                        "error": "incorrect_format",
                        "message": "You're using an outdated format for playing Spotify on Sonos. The correct format requires a nested 'media' object and the 'enqueue' parameter.",
                        "your_request": {
                            "domain": domain,
                            "service": service,
                            "data": data
                        },
                        "correct_format": {
                            "domain": "media_player",
                            "service": "play_media",
                            "data": {
                                "entity_id": entity_id,
                                "media": {
                                    "media_content_id": media_id,
                                    "media_content_type": f"spotify://{media_type}" if media_type and not media_type.startswith("spotify://") else (media_type or "spotify://playlist")
                                },
                                "enqueue": "replace"
                            }
                        },
                        "key_changes": [
                            "Wrap media_content_id and media_content_type inside a 'media' object",
                            "Add 'enqueue' parameter at the data level (same level as 'entity_id' and 'media')",
                            "Use 'spotify://' prefix for media_content_type (e.g., 'spotify://playlist')",
                            "Set enqueue to 'replace' to replace the queue and start playing immediately"
                        ],
                        "documentation": "https://www.home-assistant.io/integrations/sonos/#service-sonos-play-media"
                    }
            
            # Check for correct format with data.media
            if "media" in data and isinstance(data["media"], dict):
                media_id = data["media"].get("media_content_id")
                media_type = data["media"].get("media_content_type")
                
                # For Sonos + Spotify, require enqueue parameter
                if "sonos" in entity_id.lower() and media_id and isinstance(media_id, str):
                    is_spotify = (
                        media_id.lower().startswith("spotify:") or 
                        media_id.lower().startswith("spotify://") or
                        (media_type and "spotify" in media_type.lower())
                    )
                    
                    if is_spotify and "enqueue" not in data:
                        logger.warning(f"Missing 'enqueue' parameter for Sonos+Spotify playback")
                        return {
                            "error": "missing_required_parameter",
                            "parameter": "enqueue",
                            "message": "The 'enqueue' parameter is REQUIRED when playing Spotify content on Sonos devices. Without it, Home Assistant will return a 500 error.",
                            "your_request": {
                                "domain": domain,
                                "service": service,
                                "data": data
                            },
                            "correct_request": {
                                "domain": "media_player",
                                "service": "play_media",
                                "data": {
                                    "entity_id": entity_id,
                                    "media": {
                                        "media_content_id": media_id,
                                        "media_content_type": media_type or "spotify://playlist"
                                    },
                                    "enqueue": "replace"
                                }
                            },
                            "enqueue_options": {
                                "replace": "Replace the current queue and start playing immediately (most common)",
                                "add": "Add to the end of the queue without starting playback",
                                "next": "Play after the current track",
                                "play": "Start playing immediately"
                            },
                            "instruction": "Add the 'enqueue' parameter at the same level as 'entity_id' and 'media' in the data object, then retry the call.",
                            "documentation": "https://www.home-assistant.io/integrations/sonos/#service-sonos-play-media"
                        }

        tool_result = await call_ha_api("POST", f"/api/services/{domain}/{service}", token, data)
    
    elif tool_name == "ha_get_config":
        tool_result = await call_ha_api("GET", "/api/config", token)
    
    elif tool_name == "ha_get_logbook":
        entity_id = arguments.get("entity_id")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        
        # Build URL
        timestamp = start_time if start_time else ""
        url_path = f"/api/logbook/{timestamp}"
        
        params = []
        if entity_id:
            params.append(f"entity={entity_id}")
        if end_time:
            params.append(f"end_time={end_time}")
        
        if params:
            url_path += "?" + "&".join(params)
        
        tool_result = await call_ha_api("GET", url_path, token)
    
    elif tool_name == "ha_fire_event":
        event_type = arguments.get("event_type")
        event_data = arguments.get("event_data")
        
        if not event_type:
            raise ValueError("event_type is required")
        
        tool_result = await call_ha_api("POST", f"/api/events/{event_type}", token, event_data or {})
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    return tool_result


# Startup event
@app.on_event("startup")
async def startup():
    logger.info(f"MCP Server v{VERSION} starting with HA_BASE_URL: {HA_BASE_URL}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    await http_client.aclose()
    logger.info("MCP Server shutdown complete")
