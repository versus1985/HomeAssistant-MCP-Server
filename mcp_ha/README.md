# Home Assistant MCP Server

Model Context Protocol (MCP) server that exposes Home Assistant REST APIs as MCP tools.

## Features

- **Home Assistant Authentication**: Requires Home Assistant long-lived token
- **5 MCP Tools**:
  - `ha_list_states`: Get all entity states
  - `ha_get_state`: Get state of a specific entity
  - `ha_list_services`: Get all available services
  - `ha_call_service`: Call a Home Assistant service
  - `ha_render_template`: Render Home Assistant Jinja2 templates
- **Health Check**: `/health` endpoint without authentication
- **Streamable HTTP Transport**: Compatible with modern MCP clients

## Configuration

Before starting, go to the **Configuration** tab:

```yaml
ha_base_url: "http://homeassistant:8123"
```

The default value should work. If Home Assistant is on a different port or host, modify it.

## Startup

1. **Info** tab
2. Enable **Start on boot** (optional but recommended)
3. Enable **Watchdog** (optional)
4. Click **Start**

## Obtaining an Access Token

1. Go to Home Assistant → **Profile** (click your name in bottom left)
2. Scroll down to **Long-Lived Access Tokens**
3. Click **Create Token**
4. Give it a name (e.g., "MCP Server")
5. Copy the token (starts with `eyJ...`)

## Basic Testing

### Health Check (without authentication)

```bash
curl http://<raspi-ip>:8099/health
```

Expected response:
```json
{"status":"healthy","service":"mcp-ha-server"}
```

### Test MCP Tool List

```bash
curl -X POST http://<raspi-ip>:8099/mcp/v1/tools/list \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -H "Content-Type: application/json"
```

Expected response: list of 5 MCP tools.

## Template Notes

When using the `ha_render_template` MCP tool, make sure Jinja filters are supported by Home Assistant.

- The `avg` filter is NOT available in Home Assistant.
- Use `average` (numeric function/filter) instead as per official documentation.
- Alternatively, calculate the average manually: `sum(list) / count(list)` after converting values to numbers (e.g., `map('float')`).

Correct examples:

```jinja2
{{ [1, 2, 3, 4] | average }}
{{ ([1, 2, 3, 4] | sum) / ([1, 2, 3, 4] | count) }}
```

If you get an error like `No filter named 'avg'`, the MCP server responds with an automatic suggestion on how to fix the template.

### Handling Unknown Values

When you have sensors with `unknown` or non-numeric values:

```jinja2
# With default
{{ states.sensor | selectattr('entity_id', 'in', ['sensor.temp1', 'sensor.temp2']) 
   | map(attribute='state') | map('float', default=0) | average }}

# Filtering only valid numbers
{{ states.sensor | selectattr('entity_id', 'in', ['sensor.temp1', 'sensor.temp2']) 
   | map(attribute='state') | select('is_number') | map('float') | average(0) }}
```

## Troubleshooting

### Error 401 Unauthorized

- Verify the token is valid: go to Home Assistant → Profile → Long-Lived Access Tokens
- The token might be expired or revoked
- Make sure to use `Authorization: Bearer <token>` (with "Bearer " and space)

### Error 503 Service Unavailable

- The add-on cannot reach Home Assistant
- Verify that `ha_base_url` is correct (usually `http://homeassistant:8123`)
- Check that Home Assistant is running

### Add-on won't start

1. Check the logs in the **Log** tab
2. Verify that `ha_base_url` is correct in Configuration
3. Make sure port 8099 is not already in use

## Security

⚠️ **Warning**:
- Never expose port 8099 directly on the Internet without HTTPS
- Always use a reverse proxy (Nginx Proxy Manager, Traefik, etc.) with SSL
- Never log tokens in logs
- Revoke compromised tokens immediately from Home Assistant

## Support

For issues, questions, or feature requests, visit the project's GitHub repository.
