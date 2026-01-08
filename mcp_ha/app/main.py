import os
import json
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
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
        return response.json()
    
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
                        "description": "Get all entity states from Home Assistant",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
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
                    }
                ]
            }
        
        # Call tool
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"Tool called: {tool_name}, arguments_keys={list(arguments.keys())}")
            
            if tool_name == "ha_list_states":
                tool_result = await call_ha_api("GET", "/api/states", token)
            elif tool_name == "ha_get_state":
                entity_id = arguments.get("entity_id")
                if not entity_id:
                    raise ValueError("entity_id is required")
                tool_result = await call_ha_api("GET", f"/api/states/{entity_id}", token)
            elif tool_name == "ha_list_services":
                tool_result = await call_ha_api("GET", "/api/services", token)
            elif tool_name == "ha_call_service":
                domain = arguments.get("domain")
                service = arguments.get("service")
                data = arguments.get("data")
                if not domain or not service:
                    raise ValueError("domain and service are required")
                tool_result = await call_ha_api("POST", f"/api/services/{domain}/{service}", token, data or {})
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
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
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_id
            }
        )


# Startup event
@app.on_event("startup")
async def startup():
    logger.info(f"MCP Server starting with HA_BASE_URL: {HA_BASE_URL}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    await http_client.aclose()
    logger.info("MCP Server shutdown complete")
