# Home Assistant MCP Server

Model Context Protocol (MCP) server che espone le API REST di Home Assistant come tool MCP.

## Caratteristiche

- **Autenticazione Home Assistant**: Richiede token long-lived di Home Assistant
- **5 Tool MCP**:
  - `ha_list_states`: Ottieni tutti gli stati delle entità
  - `ha_get_state`: Ottieni lo stato di una entità specifica
  - `ha_list_services`: Ottieni tutti i servizi disponibili
  - `ha_call_service`: Chiama un servizio di Home Assistant
  - `ha_render_template`: Renderizza template Jinja2 di Home Assistant
- **Health Check**: Endpoint `/health` senza autenticazione
- **Streamable HTTP Transport**: Compatibile con client MCP moderni

## Configurazione

Prima di avviare, vai alla tab **Configuration**:

```yaml
ha_base_url: "http://homeassistant:8123"
```

Il valore di default dovrebbe funzionare. Se Home Assistant è su un'altra porta o host, modificalo.

## Avvio

1. Tab **Info**
2. Abilita **Start on boot** (opzionale ma consigliato)
3. Abilita **Watchdog** (opzionale)
4. Clicca **Start**

## Ottenere un Token di Accesso

1. Vai su Home Assistant → **Profile** (click sul tuo nome in basso a sinistra)
2. Scorri in basso fino a **Long-Lived Access Tokens**
3. Clicca **Create Token**
4. Dai un nome (es. "MCP Server")
5. Copia il token (inizia con `eyJ...`)

## Test Base

### Health Check (senza autenticazione)

```bash
curl http://<raspi-ip>:8099/health
```

Risposta attesa:
```json
{"status":"healthy","service":"mcp-ha-server"}
```

### Test MCP Tool List

```bash
curl -X POST http://<raspi-ip>:8099/mcp/v1/tools/list \
     -H "Authorization: Bearer <TUO_TOKEN>" \
     -H "Content-Type: application/json"
```

Risposta attesa: lista dei 5 tool MCP.

## Note sui Template

Quando usi il tool MCP `ha_render_template`, assicurati che i filtri Jinja siano supportati da Home Assistant.

- Il filtro `avg` NON è disponibile in Home Assistant.
- Usa invece `average` (funzione/filtro numerico) come da documentazione ufficiale.
- In alternativa, calcola la media manualmente: `sum(lista) / count(lista)` dopo aver convertito i valori in numeri (es. `map('float')`).

Esempi corretti:

```jinja2
{{ [1, 2, 3, 4] | average }}
{{ ([1, 2, 3, 4] | sum) / ([1, 2, 3, 4] | count) }}
```

Se ricevi un errore del tipo `No filter named 'avg'`, il server MCP risponde con un suggerimento automatico su come correggere il template.

### Gestione Valori Unknown

Quando hai sensori con valori `unknown` o non numerici:

```jinja2
# Con default
{{ states.sensor | selectattr('entity_id', 'in', ['sensor.temp1', 'sensor.temp2']) 
   | map(attribute='state') | map('float', default=0) | average }}

# Filtrando solo numeri validi
{{ states.sensor | selectattr('entity_id', 'in', ['sensor.temp1', 'sensor.temp2']) 
   | map(attribute='state') | select('is_number') | map('float') | average(0) }}
```

## Troubleshooting

### Errore 401 Unauthorized

- Verifica che il token sia valido: vai su Home Assistant → Profile → Long-Lived Access Tokens
- Il token potrebbe essere scaduto o revocato
- Assicurati di usare `Authorization: Bearer <token>` (con "Bearer " e spazio)

### Errore 503 Service Unavailable

- L'add-on non riesce a raggiungere Home Assistant
- Verifica che `ha_base_url` sia corretto (di solito `http://homeassistant:8123`)
- Controlla che Home Assistant sia in esecuzione

### L'add-on non si avvia

1. Controlla i log nella tab **Log**
2. Verifica che `ha_base_url` sia corretto nella Configuration
3. Assicurati che la porta 8099 non sia già in uso

## Sicurezza

⚠️ **Attenzione**:
- Non esporre mai la porta 8099 direttamente su Internet senza HTTPS
- Usa sempre un reverse proxy (Nginx Proxy Manager, Traefik, etc.) con SSL
- Non loggare mai i token nei log
- Revoca i token compromessi immediatamente da Home Assistant

## Supporto

Per problemi, domande o feature request, visita il repository GitHub del progetto.
