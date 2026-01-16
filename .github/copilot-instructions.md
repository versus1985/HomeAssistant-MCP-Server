# Copilot Instructions - Home Assistant MCP Server

## Panoramica del Progetto
Questo è un server MCP (Model Context Protocol) che espone le API REST di Home Assistant come tool MCP, permettendo agli LLM di interagire con Home Assistant.

## Architettura e Tecnologie
- **Framework**: FastAPI con Uvicorn
- **Transport**: Streamable HTTP (MCP)
- **Autenticazione**: Token long-lived di Home Assistant tramite Bearer token
- **Deployment**: Home Assistant Add-on su Docker

## Struttura del Codice
- `mcp_ha/app/main.py`: Server FastAPI principale con 4 tool MCP
- `mcp_ha/config.yaml`: Configurazione add-on Home Assistant
- `mcp_ha/Dockerfile`: Container image per l'add-on
- `mcp_ha/requirements.txt`: Dipendenze Python

## Tool MCP Implementati
1. **ha_list_states**: Recupera tutti gli stati delle entità
2. **ha_get_state**: Recupera lo stato di un'entità specifica (input: entity_id)
3. **ha_list_services**: Elenca tutti i servizi disponibili
4. **ha_call_service**: Chiama un servizio HA (input: domain, service, entity_id, service_data)

## Best Practices per Modifiche al Codice

### Gestione Autenticazione
- Usa sempre middleware `AuthMiddleware` per validare token
- L'endpoint `/health` deve rimanere senza autenticazione
- Token di HA: validare con GET `{HA_BASE_URL}/api/` prima di ogni richiesta autenticata
- Memorizza il token in `request.state.ha_token` dopo la validazione

### Chiamate API Home Assistant
- URL base: Usa sempre `HA_BASE_URL` da variabile d'ambiente
- Headers: Includi sempre `Authorization: Bearer {token}`
- Timeout: Usa `HTTP_TIMEOUT` (default 30s)
- Client: Usa `httpx.AsyncClient` riutilizzabile
- Gestisci errori di connessione con `httpx.RequestError`

### Logging
- Usa `logger.info()` per richieste e risposte normali
- Usa `logger.warning()` per problemi di autenticazione
- Usa `logger.error()` per errori critici o di connessione
- Logga sempre: method, path, status code, token validation

### Formato MCP Tool
Ogni tool deve seguire questo schema:
```python
{
    "name": "tool_name",
    "description": "Descrizione chiara dello scopo",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string/number/boolean",
                "description": "Descrizione parametro"
            }
        },
        "required": ["required_params"]
    }
}
```

### Risposte MCP Tool
Le risposte devono seguire questo formato:
```python
{
    "content": [
        {
            "type": "text",
            "text": "Risultato formattato (può essere JSON stringificato)"
        }
    ]
}
```

### Gestione Errori
- Status 401: Token mancante o invalido
- Status 503: Home Assistant non raggiungibile
- Status 400: Parametri mancanti o invalidi per tool call
- Restituisci sempre messaggi di errore chiari e informativi

### Home Assistant API Patterns
- Stati: `GET /api/states` o `GET /api/states/{entity_id}`
- Servizi disponibili: `GET /api/services`
- Chiamata servizio: `POST /api/services/{domain}/{service}` con body JSON

### Docker e Add-on
- Port mapping: Porta 8099 esposta (`EXPOSE 8099`)
- Variabili ambiente: `HA_BASE_URL` configurabile da `config.yaml`
- Network: Usa hostname `homeassistant` per comunicare con HA core
- Healthcheck: Endpoint `/health` deve rispondere 200 senza autenticazione

### Testing
- Test health: `curl http://<ip>:8099/health`
- Test con token: Includi header `Authorization: Bearer <token>`
- Test tool call: POST a `/mcp/v1/tools/call` con payload MCP corretto

## Convenzioni di Codifica
- **Lingua**: Commenti e docstring in italiano per coerenza con README
- **Stile**: Seguire PEP 8
- **Type hints**: Usa sempre type hints per parametri e return values
- **Async**: Preferisci async/await per I/O operations
- **Error handling**: Usa try-except con logging appropriato

## Estendibilità
Per aggiungere nuovi tool MCP:
1. Aggiungi definizione in lista `TOOLS` con schema completo
2. Implementa handler nel match-case di `call_tool()`
3. Valida input parameters
4. Fai chiamata API HA con `http_client.request()`
5. Formatta risposta secondo schema MCP
6. Gestisci errori appropriatamente con try-except
7. Aggiorna README.md con documentazione del nuovo tool

## Gestione Versione e Changelog
- **Versione add-on**: Definita in `mcp_ha/config.yaml` nel campo `version`
- **Formato**: Usa Semantic Versioning (MAJOR.MINOR.PATCH)
  - MAJOR: Cambiamenti breaking (es. rimozione tool, cambio API)
  - MINOR: Nuove features backward-compatible (es. nuovo tool MCP)
  - PATCH: Bug fix e miglioramenti minori
- **Quando incrementare**:
  - Ogni volta che modifichi il codice del server
  - Prima di fare commit di nuove features o fix
  - Aggiorna sempre la versione in `config.yaml` prima del deployment
- **Esempio**: `1.0.0` → `1.1.0` (nuovo tool) o `1.0.1` (bug fix)

### Aggiornamento CHANGELOG.md
- **Obbligatorio**: Aggiorna `mcp_ha/CHANGELOG.md` ad ogni modifica insieme alla versione
- **Posizione**: Il file deve stare in `mcp_ha/CHANGELOG.md` per essere visibile nella tab Changelog dell'add-on Home Assistant
- **Formato**: Segui [Keep a Changelog](https://keepachangelog.com/it/1.0.0/)
- **Categorie da usare**:
  - `Aggiunto`: Nuove funzionalità (tool MCP, feature)
  - `Modificato`: Cambiamenti a funzionalità esistenti
  - `Deprecato`: Funzionalità che saranno rimosse
  - `Rimosso`: Funzionalità rimosse
  - `Corretto`: Bug fix
  - `Sicurezza`: Vulnerabilità corrette
- **Workflow**: Quando modifichi codice:
  1. Incrementa versione in `config.yaml`
  2. Aggiungi entry in `CHANGELOG.md` sotto la nuova versione con data
  3. Descrivi la modifica nella categoria appropriata
- **Esempio entry**:
  ```markdown
  ## [1.1.0] - 2026-01-16
  
  ### Aggiunto
  - Tool `ha_trigger_automation`: possibilità di triggerare automazioni
  ```

## Note Importanti
- Il server gira inside un container Home Assistant add-on
- Non modificare l'endpoint `/health` (usato per monitoraggio)
- Token HA: sempre validato prima dell'uso, mai hardcoded
- HA_BASE_URL: di default `http://homeassistant:8123` (rete interna add-on)
- **Versione**: Ricordati di incrementare la versione in `config.yaml` ad ogni modifica
