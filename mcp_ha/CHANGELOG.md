# Changelog

Tutte le modifiche notevoli a questo progetto saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/lang/it/).

## [1.3.4] - 2026-01-16

### Modificato
- **Gestione errori agent-friendly per tutti i tool**: tutti i tool MCP ora restituiscono 200 con payload di errore strutturato (error, status_code, message, suggestion) invece di HTTP 4xx quando l'API HA fallisce, permettendo agli AI agent di interpretare e agire sugli errori.
- Centralizzata l'esecuzione dei tool nella funzione `execute_tool()` che cattura `HTTPException` e le converte in risposte 200 con informazioni contestuali.
- Aggiunta funzione helper `get_error_suggestion()` che fornisce suggerimenti contestuali basati su status code, messaggio di errore, tool name e parametri (es. per 404 su entity suggerisce di usare `ha_list_states`).

## [1.3.3] - 2026-01-16

### Corretto
- `call_ha_api`: gestisce risposte non-JSON (es. `/api/template`) con fallback a `response.text`, evitando JSONDecodeError e risposte 400.

## [1.3.2] - 2026-01-16

### Modificato
- `ha_render_template`: in caso di errore di rendering, il server ora risponde 200 con una spiegazione strutturata (message, suggestion, docs_url) per migliorare l'interoperabilità con agent runtime che non interpretano 400.

## [1.3.1] - 2026-01-16

### Corretto
- Migliorati suggerimenti per errori di rendering template quando `float` riceve valori non numerici (es. `unknown`) e non è specificato un `default`. Indicazioni su `map('float', default=0)`, `select('is_number')` e `average(0)`.

## [1.3.0] - 2026-01-16

### Modificato
- `ha_render_template`: migliorata la gestione errori per filtri Jinja non supportati con suggerimenti automatici (es. `avg` → usare `average`)
- Documentazione aggiornata con esempi di `average` e calcolo manuale della media

## [1.2.3] - 2026-01-16

### Corretto
- Aggiunto config.yaml al Dockerfile per permettere la lettura della versione
- Aggiunto fallback nella funzione get_version() per cercare in più percorsi

## [1.2.2] - 2026-01-16

### Aggiunto
- Stampa della versione all'avvio del server nel log
- Dipendenza pyyaml per leggere la versione dal config.yaml

## [1.2.1] - 2026-01-16

### Corretto
- Aggiunto endpoint SSE su `/mcp` per supportare correttamente il protocollo MCP Streamable HTTP
- Risolto errore 307 redirect quando client MCP si connette all'endpoint principale

## [1.2.0] - 2026-01-16

### Aggiunto
- Copilot instructions per guidare lo sviluppo futuro
- CHANGELOG.md per tracciare le modifiche

## [1.0.0] - 2026-01-16

### Aggiunto
- Server MCP iniziale con 4 tool per Home Assistant
- Tool `ha_list_states`: elenca tutti gli stati delle entità
- Tool `ha_get_state`: recupera lo stato di un'entità specifica
- Tool `ha_list_services`: elenca tutti i servizi disponibili
- Tool `ha_call_service`: chiama un servizio di Home Assistant
- Autenticazione tramite token long-lived di Home Assistant
- Endpoint `/health` per monitoring
- Supporto Streamable HTTP Transport (MCP)
- Home Assistant Add-on configuration
