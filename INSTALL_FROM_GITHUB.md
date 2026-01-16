# Installazione Add-on da GitHub Repository

## Setup Repository GitHub in Home Assistant

### 1. Aggiungi il Repository GitHub

1. Vai su **Home Assistant** → **Settings** → **Add-ons** → **Add-on Store**
2. Click sul menu (3 punti in alto a destra)
3. Click su **Repositories**
4. Aggiungi questo URL:
   ```
   https://github.com/versus1985/HomeAssistant-MCP-Server
   ```
5. Click **Add**
6. Attendi qualche secondo per il refresh

### 2. Installa l'Add-on

1. Torna all'**Add-on Store**
2. Cerca nella sezione repository GitHub appena aggiunto
3. Troverai **MCP Server for Home Assistant**
4. Click sull'add-on
5. Click **Install**
   - ⚠️ **Importante**: Con il campo `image` in `config.yaml`, HA scaricherà l'immagine pre-buildata da GHCR invece di buildarla localmente

### 3. Configura l'Add-on

1. Vai alla tab **Configuration**
2. Lascia i default (dovrebbe andare bene):
   ```yaml
   ha_base_url: "http://homeassistant:8123"
   ```
3. Se necessario, modifica con l'URL corretto

### 4. Avvia l'Add-on

1. Torna alla tab **Info**
2. Abilita **Start on boot** (consigliato)
3. Abilita **Watchdog** (consigliato)
4. Click **Start**

### 5. Verifica Installazione

1. Vai alla tab **Log**
2. Dovresti vedere:
   ```
   Starting MCP Server for Home Assistant...
   HA Base URL: http://homeassistant:8123
   INFO:     Started server process [1]
   INFO:     Uvicorn running on http://0.0.0.0:8099
   ```

## Rimozione Installazione Locale (se presente)

Se hai già un'installazione locale, rimuovila prima:

### Da UI Home Assistant

1. **Settings** → **Add-ons**
2. Trova l'add-on MCP Server installato localmente
3. Click sull'add-on
4. Tab **Info**
5. Click **Uninstall**
6. Conferma

### Rimuovi Repository Locale (opzionale)

Se avevi aggiunto il repository locale (`file:///addons/...`):

1. **Add-on Store** → Menu (3 punti) → **Repositories**
2. Trova il repository locale (es. `file:///addons/ha-addon-mcp`)
3. Click sulla X per rimuoverlo

### Da Terminal & SSH (alternativa)

```bash
# Disinstalla add-on
ha addons uninstall local_mcp_ha

# Rimuovi cartella locale (se presente)
rm -rf /addons/ha-addon-mcp
# oppure
rm -rf /config/custom_addons/ha-addon-mcp
```

## Verifica Sorgente Installazione

Dopo l'installazione, verifica che stia usando GHCR:

```bash
# Da Terminal & SSH
ha addons info mcp_ha --raw-json | jq '.data.repository'
```

Dovrebbe mostrare il repository GitHub invece di "local".

## Aggiornamenti Futuri

Con questa configurazione:

1. **Tu fai push** su GitHub → GitHub Actions builda e pusha su GHCR
2. **Home Assistant** controllerà automaticamente gli aggiornamenti da GHCR
3. **Vedrai notifica** "Update available" quando c'è una nuova versione
4. **Click Update** → Scarica nuova immagine (nessun rebuild locale!)

### Forza Check Aggiornamenti

Da Terminal & SSH:
```bash
ha supervisor reload
ha addons info mcp_ha
```

Da UI:
- Add-ons → Menu → **Check for updates**

## Troubleshooting

### "Repository not found" o "404"

Verifica che:
1. Il repository GitHub sia **pubblico**
2. L'URL sia corretto: `https://github.com/versus1985/HomeAssistant-MCP-Server`
3. Il file `mcp_ha/config.yaml` sia presente nella root del repository

### "Cannot pull image" o "Image not found"

L'immagine su GHCR deve essere pubblica:

1. Vai su: `https://github.com/versus1985?tab=packages`
2. Click su `homeassistant-mcp-server`
3. **Package settings** (in basso a destra)
4. Scorri fino a "Danger Zone"
5. **Change visibility** → **Public**
6. Conferma

### Verifica Connettività GHCR

Da Terminal & SSH:
```bash
curl -I https://ghcr.io/v2/versus1985/homeassistant-mcp-server/manifests/latest
```

Deve rispondere **200** se pubblico, **401/404** se privato o non trovato.

### L'add-on non appare dopo aver aggiunto il repository

1. Controlla che `mcp_ha/config.yaml` sia presente
2. Verifica che il campo `slug: mcp_ha` sia corretto
3. Fai refresh forzato: rimuovi e ri-aggiungi il repository
4. Controlla i log del Supervisor:
   ```bash
   ha supervisor logs
   ```

## Passaggio da Build Locale a Registry

Se hai già l'add-on installato localmente e vuoi passare alla versione GitHub:

1. **Non serve disinstallare** se lo slug è lo stesso (`mcp_ha`)
2. Aggiungi il repository GitHub come sopra
3. Home Assistant riconoscerà che è lo stesso add-on
4. La prossima volta che aggiorni, userà l'immagine da GHCR invece di rebuildar

Oppure per essere sicuro:
1. Disinstalla versione locale
2. Aggiungi repository GitHub
3. Reinstalla da GitHub repository
