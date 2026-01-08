# Home Assistant MCP Server Add-on

Model Context Protocol (MCP) server che espone le API REST di Home Assistant come tool MCP.

## Caratteristiche

- **Autenticazione Home Assistant**: Richiede token long-lived di Home Assistant
- **4 Tool MCP**:
  - `ha_list_states`: Ottieni tutti gli stati delle entità
  - `ha_get_state`: Ottieni lo stato di una entità specifica
  - `ha_list_services`: Ottieni tutti i servizi disponibili
  - `ha_call_service`: Chiama un servizio di Home Assistant
- **Health Check**: Endpoint `/health` senza autenticazione
- **Streamable HTTP Transport**: Compatibile con client MCP moderni

## Installazione

### 1. Copiare il repository nell'add-on folder di Home Assistant

Connettiti al tuo Raspberry Pi via SSH o usa l'add-on Terminal & SSH di Home Assistant.

```bash
cd /addons
git clone <questo-repo> ha-addon-mcp
# Oppure copia manualmente la cartella mcp_ha/
```

Se copi manualmente, assicurati che la struttura sia:
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

### 2. Aggiungere il repository locale in Home Assistant

1. Vai su **Settings** → **Add-ons** → **Add-on Store**
2. Menu (3 punti in alto a destra) → **Repositories**
3. Aggiungi: `file:///addons/ha-addon-mcp`
4. Clicca **Add**

Oppure, se hai clonato in `/config/custom_addons/`:
```
file:///config/custom_addons/ha-addon-mcp
```

### 3. Installare l'add-on

1. Torna all'Add-on Store
2. Cerca **MCP Server for Home Assistant** nella sezione **Local add-ons**
3. Clicca sull'add-on
4. Clicca **Install**

### 4. Configurazione

Prima di avviare, vai alla tab **Configuration**:

```yaml
ha_base_url: "http://homeassistant:8123"
```

Il valore di default dovrebbe funzionare. Se Home Assistant è su un'altra porta o host, modificalo.

### 5. Avviare l'add-on

1. Tab **Info**
2. Abilita **Start on boot** (opzionale ma consigliato)
3. Abilita **Watchdog** (opzionale)
4. Clicca **Start**

### 6. Verificare i log

Vai alla tab **Log** per vedere:
```
Starting MCP Server for Home Assistant...
HA Base URL: http://homeassistant:8123
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     MCP Server starting with HA_BASE_URL: http://homeassistant:8123
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8099
```

## Test in LAN

### 1. Ottieni un token long-lived

1. Vai su Home Assistant → **Profile** (click sul tuo nome in basso a sinistra)
2. Scorri in basso fino a **Long-Lived Access Tokens**
3. Clicca **Create Token**
4. Dai un nome (es. "MCP Server")
5. Copia il token (inizia con `eyJ...`)

### 2. Test health endpoint (senza auth)

```bash
curl http://<raspi-ip>:8099/health
```

Risposta attesa:
```json
{"status":"healthy","service":"mcp-ha-server"}
```

### 3. Test con autenticazione

```bash
curl -H "Authorization: Bearer <TUO_TOKEN>" \
     http://<raspi-ip>:8099/health
```

Dovrebbe funzionare anche con auth (middleware salta /health).

### 4. Test MCP endpoint (POST /messages)

```bash
curl -X POST http://<raspi-ip>:8099/messages \
     -H "Authorization: Bearer <TUO_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list"
     }'
```

Risposta attesa: lista dei 4 tool MCP.

## Esposizione su Internet con Nginx Proxy Manager

### Prerequisiti

- Nginx Proxy Manager già installato e configurato
- Proxy Host esistente per `sagostini.ddns.net` che punta a `homeassistant:8123`
- SSL attivo con certificato Let's Encrypt

### Configurazione Nginx Proxy Manager

#### 1. Apri il Proxy Host esistente per sagostini.ddns.net

- Vai su **Hosts** → **Proxy Hosts**
- Modifica il proxy host per `sagostini.ddns.net`

#### 2. Aggiungi Custom Location

Vai alla tab **Custom Locations** e clicca **Add Custom Location**:

- **Location**: `/mcp/`
- **Scheme**: `http`
- **Forward Hostname / IP**: `<raspi-lan-ip>` (es. `192.168.1.100` o usa `homeassistant.local` se risolve)
- **Forward Port**: `8099`
- **Forward Path**: `/` (importante: slash finale)

Opzioni avanzate (checkboxes):
- ✅ **Websockets Support**: OFF (non necessario per MCP HTTP)
- ✅ **Block Common Exploits**: ON
- ✅ **Pass Host Header**: OFF

#### 3. Advanced Configuration

Clicca sulla tab **Advanced** del Custom Location e aggiungi:

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

#### 4. Salva

Clicca **Save** per applicare la configurazione.

### Test Esterno

#### 1. Test health endpoint

```bash
curl https://sagostini.ddns.net/mcp/health
```

Risposta attesa:
```json
{"status":"healthy","service":"mcp-ha-server"}
```

#### 2. Test con autenticazione

```bash
curl -H "Authorization: Bearer <TUO_TOKEN>" \
     https://sagostini.ddns.net/mcp/health
```

#### 3. Test MCP tool list

```bash
curl -X POST https://sagostini.ddns.net/mcp/messages \
     -H "Authorization: Bearer <TUO_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list"
     }'
```

Risposta attesa: JSON con array di 4 tool (ha_list_states, ha_get_state, ha_list_services, ha_call_service).

#### 4. Test chiamata tool (get all states)

```bash
curl -X POST https://sagostini.ddns.net/mcp/messages \
     -H "Authorization: Bearer <TUO_TOKEN>" \
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

Risposta attesa: JSON con tutti gli stati delle entità di Home Assistant.

## Troubleshooting

### L'add-on non si avvia

1. Controlla i log: **Add-ons** → **MCP Server for Home Assistant** → **Log**
2. Verifica che `ha_base_url` sia corretto nella Configuration
3. Assicurati che la porta 8099 non sia già in uso

### Errore 401 Unauthorized

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

### Modificare il codice

I file sorgenti sono in `mcp_ha/app/main.py`. Per applicare modifiche:

1. Modifica il file
2. Incrementa la versione in `config.yaml`
3. Ricostruisci l'add-on: **Add-ons** → **MCP Server** → **Rebuild**
4. Riavvia l'add-on

### Aggiungere nuovi tool MCP

Modifica `main.py`:

1. Aggiungi il tool nella funzione `list_tools()`
2. Aggiungi la logica nella funzione `call_tool()`
3. Testa localmente prima di deployare

## Sicurezza

⚠️ **Attenzione**:
- Non esporre mai la porta 8099 direttamente su Internet senza HTTPS
- Usa sempre Nginx Proxy Manager o reverse proxy simile con SSL
- Non loggare mai i token nei log
- Revoca i token compromessi immediatamente da Home Assistant

## Licenza

MIT License - Usa liberamente per scopi personali e commerciali.

## Supporto

Per problemi o domande, apri un issue su GitHub.
