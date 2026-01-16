# Copilot Instructions - Home Assistant MCP Server

## Project Overview
This is an MCP (Model Context Protocol) server that exposes Home Assistant REST APIs as MCP tools, allowing LLMs to interact with Home Assistant.

## Architecture and Technologies
- **Framework**: FastAPI with Uvicorn
- **Transport**: Streamable HTTP (MCP)
- **Authentication**: Home Assistant long-lived token via Bearer token
- **Deployment**: Home Assistant Add-on on Docker

## Code Structure
- `mcp_ha/app/main.py`: Main FastAPI server with 4 MCP tools
- `mcp_ha/config.yaml`: Home Assistant add-on configuration
- `mcp_ha/Dockerfile`: Container image for the add-on
- `mcp_ha/requirements.txt`: Python dependencies

## Implemented MCP Tools
1. **ha_list_states**: Retrieves all entity states
2. **ha_get_state**: Retrieves the state of a specific entity (input: entity_id)
3. **ha_list_services**: Lists all available services
4. **ha_call_service**: Calls an HA service (input: domain, service, entity_id, service_data)

## Best Practices for Code Modifications

### Authentication Management
- Always use `AuthMiddleware` middleware to validate token
- The `/health` endpoint must remain without authentication
- HA Token: validate with GET `{HA_BASE_URL}/api/` before every authenticated request
- Store the token in `request.state.ha_token` after validation

### Home Assistant API Calls
- Base URL: Always use `HA_BASE_URL` from environment variable
- Headers: Always include `Authorization: Bearer {token}`
- Timeout: Use `HTTP_TIMEOUT` (default 30s)
- Client: Use reusable `httpx.AsyncClient`
- Handle connection errors with `httpx.RequestError`

### Logging
- Use `logger.info()` for normal requests and responses
- Use `logger.warning()` for authentication issues
- Use `logger.error()` for critical or connection errors
- Always log: method, path, status code, token validation

### MCP Tool Format
Each tool must follow this schema:
```python
{
    "name": "tool_name",
    "description": "Clear description of the purpose",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string/number/boolean",
                "description": "Parameter description"
            }
        },
        "required": ["required_params"]
    }
}
```

### MCP Tool Responses
Responses must follow this format:
```python
{
    "content": [
        {
            "type": "text",
            "text": "Formatted result (can be stringified JSON)"
        }
    ]
}
```

### Error Handling
- Status 401: Missing or invalid token
- Status 503: Home Assistant unreachable
- Status 400: Missing or invalid parameters for tool call
- Always return clear and informative error messages

### Home Assistant API Patterns
- States: `GET /api/states` or `GET /api/states/{entity_id}`
- Available services: `GET /api/services`
- Service call: `POST /api/services/{domain}/{service}` with JSON body

### Docker and Add-on
- Port mapping: Port 8099 exposed (`EXPOSE 8099`)
- Environment variables: `HA_BASE_URL` configurable from `config.yaml`
- Network: Use hostname `homeassistant` to communicate with HA core
- Healthcheck: `/health` endpoint must respond 200 without authentication

### Testing
- Test health: `curl http://<ip>:8099/health`
- Test with token: Include header `Authorization: Bearer <token>`
- Test tool call: POST to `/mcp/v1/tools/call` with correct MCP payload

## Coding Conventions
- **Language**: Comments and docstrings in English for consistency with README
- **Style**: Follow PEP 8
- **Type hints**: Always use type hints for parameters and return values
- **Async**: Prefer async/await for I/O operations
- **Error handling**: Use try-except with appropriate logging

## Extensibility
To add new MCP tools:
1. Add definition in `TOOLS` list with complete schema
2. Implement handler in the match-case of `call_tool()`
3. Validate input parameters
4. Make HA API call with `http_client.request()`
5. Format response according to MCP schema
6. Handle errors appropriately with try-except
7. Update README.md with new tool documentation

## Version and Changelog Management
- **Add-on version**: Defined in `mcp_ha/config.yaml` in the `version` field
- **Format**: Use Semantic Versioning (MAJOR.MINOR.PATCH)
  - MAJOR: Breaking changes (e.g., tool removal, API change)
  - MINOR: New backward-compatible features (e.g., new MCP tool)
  - PATCH: Bug fixes and minor improvements
- **When to increment**:
  - **ALWAYS** increment version with every code modification
  - Before committing new features or fixes
  - Version must be updated in `config.yaml` before git push
- **Example**: `1.0.0` → `1.1.0` (new tool) or `1.0.1` (bug fix)

### Updating CHANGELOG.md
- **Mandatory**: Update `mcp_ha/CHANGELOG.md` with every modification along with the version
- **Location**: The file must be in `mcp_ha/CHANGELOG.md` to be visible in the Changelog tab of the Home Assistant add-on
- **Format**: Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- **Categories to use**:
  - `Added`: New features (MCP tools, features)
  - `Changed`: Changes to existing features
  - `Deprecated`: Features that will be removed
  - `Removed`: Removed features
  - `Fixed`: Bug fixes
  - `Security`: Fixed vulnerabilities
- **Workflow**: When modifying code:
  1. Increment version in `config.yaml`
  2. Add entry in `CHANGELOG.md` under the new version with date
  3. Describe the modification in the appropriate category
  4. Commit and push to `main` branch
- **Example entry**:
  ```markdown
  ## [1.1.0] - 2026-01-16
  
  ### Added
  - Tool `ha_trigger_automation`: ability to trigger automations
  ```

## Deployment Process
- **CI/CD**: GitHub Actions automatically builds and deploys on push to `main` branch
- **Multi-arch**: Automatic Docker image build for amd64, arm64, armv7
- **Registry**: Images published to GitHub Container Registry (GHCR) at `ghcr.io/versus1985/homeassistant-mcp-server`
- **Workflow**:
  1. Make code changes
  2. Update version in `config.yaml`
  3. Update `CHANGELOG.md`
  4. Commit and push to `main`
  5. GitHub Actions automatically builds and publishes new version
  6. Home Assistant add-on updates automatically from registry
- **Important**: Never use `force-update.ps1` script for deployment - always deploy via git push

## Important Notes
- The server runs inside a Home Assistant add-on container
- Do not modify the `/health` endpoint (used for monitoring)
- HA Token: always validated before use, never hardcoded
- HA_BASE_URL: defaults to `http://homeassistant:8123` (internal add-on network)
- **Version**: ALWAYS increment the version in `config.yaml` with every modification
- **Deployment**: Always deploy via `git push` to main branch, never use force-update.ps1 script
