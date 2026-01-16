# Home Assistant MCP Server - Developer Documentation

Model Context Protocol (MCP) server that exposes Home Assistant REST APIs as MCP tools.

## Architecture

- **Framework**: FastAPI with Uvicorn
- **Transport**: MCP Streamable HTTP
- **Authentication**: Home Assistant long-lived token via Bearer token
- **Deployment**: Home Assistant Add-on on Docker
- **Port**: 8099 (exposed by container)

## Project Structure

```
HomeAssistant-MCP-Server/
├── README.md                    # Developer documentation
├── .github/
│   └── copilot-instructions.md  # GitHub Copilot instructions
└── mcp_ha/                      # Home Assistant Add-on
    ├── README.md                # User documentation (visible in HA)
    ├── CHANGELOG.md             # Changelog (visible in HA)
    ├── config.yaml              # HA add-on configuration
    ├── Dockerfile               # Container image
    ├── requirements.txt         # Python dependencies
    ├── run.sh                   # Startup script
    └── app/
        └── main.py              # FastAPI server + MCP tools
```

## Implemented MCP Tools

1. **ha_list_states**: Retrieves all HA entity states
2. **ha_get_state**: Retrieves the state of a specific entity (input: entity_id)
3. **ha_list_services**: Lists all available services
4. **ha_call_service**: Calls an HA service (input: domain, service, entity_id, service_data)
5. **ha_render_template**: Renders Home Assistant Jinja2 templates (input: template)

## Agent-Friendly Error Handling

All MCP tools **always return status 200** even when the Home Assistant API returns an error. Errors are returned as structured payload:

```json
{
  "content": [{
    "type": "text",
    "text": "{\"error\": \"not_found\", \"status_code\": 404, \"message\": \"...\", \"suggestion\": \"...\"}"
  }]
}
```

This allows AI agents to interpret errors and act accordingly (e.g., retrieving the entity list with `ha_list_states` first if an entity_id doesn't exist).

## Installation

### 1. Copy the repository to Home Assistant add-on folder

Connect to your Raspberry Pi via SSH or use the Terminal & SSH add-on from Home Assistant.

```bash
cd /addons
git clone <this-repo> ha-addon-mcp
# Or manually copy the mcp_ha/ folder
```

If copying manually, ensure the structure is:
```
/addons/ha-addon-mcp/
  mcp_ha/
    config.yaml
    Dockerfile
    requirements.txt
    run.sh
    app/
      main.py
```

### 2. Add the local repository in Home Assistant

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Menu (3 dots in top right) → **Repositories**
3. Add: `file:///addons/ha-addon-mcp`
4. Click **Add**

Alternatively, if you cloned to `/config/custom_addons/`:
```
file:///config/custom_addons/ha-addon-mcp
```

### 3. Install the add-on

1. Return to the Add-on Store
2. Look for **MCP Server for Home Assistant** in the **Local add-ons** section
3. Click on the add-on
4. Click **Install**

### 4. Configuration

Before starting, go to the **Configuration** tab:

```yaml
ha_base_url: "http://homeassistant:8123"
```

The default value should work. If Home Assistant is on a different port or host, modify it.

### 5. Start the add-on

1. **Info** tab
2. Enable **Start on boot** (optional but recommended)
3. Enable **Watchdog** (optional)
4. Click **Start**

### 6. Check the logs

Go to the **Log** tab to see:
```
Starting MCP Server for Home Assistant...
HA Base URL: http://homeassistant:8123
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     MCP Server starting with HA_BASE_URL: http://homeassistant:8123
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8099
```

## LAN Testing

### 1. Obtain a long-lived token

1. Go to Home Assistant → **Profile** (click your name in bottom left)
2. Scroll down to **Long-Lived Access Tokens**
3. Click **Create Token**
4. Give it a name (e.g., "MCP Server")
5. Copy the token (starts with `eyJ...`)

### 2. Test health endpoint (without auth)

```bash
curl http://<raspi-ip>:8099/health
```

Expected response:
```json
{"status":"healthy","service":"mcp-ha-server"}
```

### 3. Test with authentication

```bash
curl -H "Authorization: Bearer <YOUR_TOKEN>" \
     http://<raspi-ip>:8099/health
```

Should work with auth too (middleware skips /health).

### 4. Test MCP endpoint (POST /messages)

```bash
curl -X POST http://<raspi-ip>:8099/messages \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list"
     }'
```

Expected response: list of 4 MCP tools.

## Internet Exposure with Nginx Proxy Manager

### Prerequisites

- Nginx Proxy Manager already installed and configured
- Existing Proxy Host for your domain pointing to `homeassistant:8123`
- Active SSL with Let's Encrypt certificate

### Nginx Proxy Manager Configuration

#### 1. Open the existing Proxy Host for your domain

- Go to **Hosts** → **Proxy Hosts**
- Edit the proxy host for your domain

#### 2. Add Custom Location

Go to the **Custom Locations** tab and click **Add Custom Location**:

- **Location**: `/mcp/`
- **Scheme**: `http`
- **Forward Hostname / IP**: `<raspi-lan-ip>` (e.g., `192.168.1.100` or use `homeassistant.local` if it resolves)
- **Forward Port**: `8099`
- **Forward Path**: `/` (important: trailing slash)

Advanced options (checkboxes):
- ✅ **Websockets Support**: OFF (not needed for MCP HTTP)
- ✅ **Block Common Exploits**: ON
- ✅ **Pass Host Header**: OFF

#### 3. Advanced Configuration

Click the **Advanced** tab of the Custom Location and add:

```nginx
# Pass Authorization header
proxy_set_header Authorization $http_authorization;

# Disable buffering for streaming
proxy_buffering off;
proxy_cache off;

# Increase timeout for long-running operations
proxy_read_timeout 3600s;
proxy_connect_timeout 60s;
proxy_send_timeout 3600s;

# Pass client IP
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

#### 4. Save

Click **Save** to apply the configuration.

### External Testing

#### 1. Test health endpoint

```bash
curl https://yourdomain.com/mcp/health
```

Expected response:
```json
{"status":"healthy","service":"mcp-ha-server"}
```

#### 2. Test with authentication

```bash
curl -H "Authorization: Bearer <YOUR_TOKEN>" \
     https://yourdomain.com/mcp/health
```

#### 3. Test MCP tool list

```bash
curl -X POST https://yourdomain.com/mcp/messages \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list"
     }'
```

Expected response: JSON with array of 4 tools (ha_list_states, ha_get_state, ha_list_services, ha_call_service).

#### 4. Test tool call (get all states)

```bash
curl -X POST https://yourdomain.com/mcp/messages \
     -H "Authorization: Bearer <YOUR_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "ha_list_states",
         "arguments": {}
       }
     }'
```

Expected response: JSON with all Home Assistant entity states.

## Troubleshooting

### Add-on won't start

1. Check the logs: **Add-ons** → **MCP Server for Home Assistant** → **Log**
2. Verify that `ha_base_url` is correct in Configuration
3. Make sure port 8099 is not already in use

### Error 401 Unauthorized

- Verifica che il token sia valido: vai su Home Assistant → Profile → Long-Lived Access Tokens
- Il token potrebbe essere scaduto o revocato
- Assicurati di usare `Authorization: Bearer <token>` (con "Bearer " e spazio)

### Errore 503 Service Unavailable

- L'add-on non riesce a raggiungere Home Assistant
- Verifica che `ha_base_url` sia corretto (di solito `http://homeassistant:8123`)
- Controlla che Home Assistant sia in esecuzione

### Nginx non passa l'header Authorization

- Verifica la configurazione Advanced del Custom Location
- Assicurati che contenga: `proxy_set_header Authorization $http_authorization;`
- Riavvia Nginx Proxy Manager dopo le modifiche

### Path non funziona (/mcp/ ritorna 404)

- Verifica che Forward Path sia `/` (con slash finale)
- Verifica che Location sia `/mcp/` (con slash finale)
- Il path mapping dovrebbe essere: `/mcp/health` → `/health`

## Sviluppo

### CI/CD Automatizzato con GitHub Actions

Il progetto è configurato per il **deployment automatico su GitHub Container Registry (GHCR)**:

1. **Ad ogni push su `main`** (che modifica file in `mcp_ha/`):
   - Build automatico dell'immagine Docker multi-arch (amd64, arm64, armv7)
   - Push su `ghcr.io/<username>/homeassistant-mcp-server`
   - Tag automatico con versione da `config.yaml` + `latest`
   - Creazione release GitHub automatica

2. **Home Assistant rileva automaticamente gli aggiornamenti** quando:
   - Incrementi la versione in `mcp_ha/config.yaml`
   - Fai push su GitHub
   - L'add-on mostra notifica di aggiornamento disponibile

3. **Per skipare la release automatica** (es. commit di docs):
   ```bash
   git commit -m "docs: update README [skip-release]"
   ```

### Setup Iniziale GitHub Actions

**Prima di fare il primo push**, configura il repository:

1. **Abilita GitHub Container Registry**:
   - Il workflow usa `GITHUB_TOKEN` (già disponibile, nessuna configurazione necessaria)
   - Le immagini saranno pubbliche di default su `ghcr.io/<username>/homeassistant-mcp-server`

2. **Permessi del repository**:
   - Settings → Actions → General → Workflow permissions
   - Seleziona **Read and write permissions**
   - Salva

3. **Visibilità del package**:
   - Dopo il primo build, vai su GitHub → Packages
   - Trova `homeassistant-mcp-server`
   - Settings → Change visibility → Public (se vuoi renderlo pubblico)

### Development Workflow

```bash
# 1. Modify the code
vim mcp_ha/app/main.py

# 2. Increment version
vim mcp_ha/config.yaml  # e.g., 1.3.5 → 1.3.6

# 3. Update CHANGELOG
vim mcp_ha/CHANGELOG.md

# 4. Commit and push
git add .
git commit -m "feat: add new tool ha_trigger_automation"
git push origin main

# 5. GitHub Actions will build and push automatically
# 6. Home Assistant will detect the update within 24h (or manually)
```

### Local Pre-Deploy Testing

Before pushing, test locally:

```bash
# Local build
cd mcp_ha
docker build -t mcp-ha-local:test .

# Test
docker run --rm -p 8099:8099 \
  -e HA_BASE_URL=http://homeassistant:8123 \
  mcp-ha-local:test

# Verify
curl http://localhost:8099/health
```

### Modifying the code

Source files are in `mcp_ha/app/main.py`. To apply changes:

**Method 1: Automatic Deployment (Recommended)**
1. Modify the file
2. Increment the version in `config.yaml`
3. Update `CHANGELOG.md`
4. Commit and push to GitHub
5. Wait for automatic build (2-5 minutes)
6. Home Assistant will show update available notification

**Method 2: Local Rebuild (For quick tests)**
1. Modify the file
2. Increment the version in `config.yaml`
3. Rebuild the add-on: **Add-ons** → **MCP Server** → **Rebuild**
4. Restart the add-on

### Adding new MCP tools

Modify `main.py`:

1. Add the tool in the `list_tools()` function
2. Add the logic in the `call_tool()` function
3. Test locally before deploying

## Security

⚠️ **Warning**:
- Never expose port 8099 directly on the Internet without HTTPS
- Always use Nginx Proxy Manager or similar reverse proxy with SSL
- Never log tokens in logs
- Revoke compromised tokens immediately from Home Assistant

## License

MIT License - Use freely for personal and commercial purposes.

## Support

For issues or questions, open an issue on GitHub.
