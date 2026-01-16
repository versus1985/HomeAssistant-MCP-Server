# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.4.0] - 2026-01-16

### Added
- **Automated CI/CD with GitHub Actions**: on every push to `main`, automatic multi-arch Docker image build (amd64, arm64, armv7) and push to GitHub Container Registry (GHCR).
- **Automatic GitHub releases**: automatic GitHub release creation with version tag when pushing (skippable with `[skip-release]` in commit message).
- **Auto-update from registry**: Home Assistant can now download updates automatically from `ghcr.io` without local rebuild.

### Changed
- `config.yaml`: added `image` field to use pre-built images from GitHub Container Registry.
- `config.yaml`: added `url` field with link to GitHub repository.

## [1.3.5] - 2026-01-16

### Changed
- Detailed logging of payloads for `ha_call_service` to facilitate debugging of Home Assistant calls.
- Automatic normalization of Spotify URIs (`Spotify:` → `spotify:`) before sending `media_player.play_media` to Home Assistant.
- Improved error suggestions for status code 500, with specific messages for `media_player.play_media` guiding verification of device, URI format, and Spotify authentication.

## [1.3.4] - 2026-01-16

### Changed
- **Agent-friendly error handling for all tools**: all MCP tools now return 200 with structured error payload (error, status_code, message, suggestion) instead of HTTP 4xx when HA API fails, allowing AI agents to interpret and act on errors.
- Centralized tool execution in `execute_tool()` function that captures `HTTPException` and converts them to 200 responses with contextual information.
- Added `get_error_suggestion()` helper function that provides contextual suggestions based on status code, error message, tool name, and parameters (e.g., for 404 on entity suggests using `ha_list_states`).

## [1.3.3] - 2026-01-16

### Fixed
- `call_ha_api`: handles non-JSON responses (e.g., `/api/template`) with fallback to `response.text`, avoiding JSONDecodeError and 400 responses.

## [1.3.2] - 2026-01-16

### Changed
- `ha_render_template`: in case of rendering error, the server now responds 200 with a structured explanation (message, suggestion, docs_url) to improve interoperability with agent runtimes that don't interpret 400.

## [1.3.1] - 2026-01-16

### Fixed
- Improved suggestions for template rendering errors when `float` receives non-numeric values (e.g., `unknown`) and no `default` is specified. Guidance on `map('float', default=0)`, `select('is_number')`, and `average(0)`.

## [1.3.0] - 2026-01-16

### Changed
- `ha_render_template`: improved error handling for unsupported Jinja filters with automatic suggestions (e.g., `avg` → use `average`)
- Updated documentation with examples of `average` and manual average calculation

## [1.2.3] - 2026-01-16

### Fixed
- Added config.yaml to Dockerfile to allow version reading
- Added fallback in get_version() function to search in multiple paths

## [1.2.2] - 2026-01-16

### Added
- Version printing at server startup in the log
- pyyaml dependency to read version from config.yaml

## [1.2.1] - 2026-01-16

### Fixed
- Added SSE endpoint on `/mcp` to properly support MCP Streamable HTTP protocol
- Fixed 307 redirect error when MCP client connects to main endpoint

## [1.2.0] - 2026-01-16

### Added
- Copilot instructions to guide future development
- CHANGELOG.md to track changes

## [1.0.0] - 2026-01-16

### Added
- Initial MCP server with 4 tools for Home Assistant
- Tool `ha_list_states`: list all entity states
- Tool `ha_get_state`: retrieve state of a specific entity
- Tool `ha_list_services`: list all available services
- Tool `ha_call_service`: call a Home Assistant service
- Authentication via Home Assistant long-lived token
- `/health` endpoint for monitoring
- Streamable HTTP Transport support (MCP)
- Home Assistant Add-on configuration
