#!/bin/bash

# Script per forzare l'aggiornamento dell'add-on MCP Server in Home Assistant
# Uso: ./force-update.sh <ip-home-assistant> <long-lived-token>

set -e

if [ "$#" -lt 2 ]; then
    echo "Uso: $0 <ip-home-assistant> <long-lived-token> [addon-slug]"
    echo ""
    echo "Esempio:"
    echo "  $0 192.168.1.100 eyJhbGc..."
    echo ""
    exit 1
fi

HA_HOST="$1"
HA_TOKEN="$2"
ADDON_SLUG="${3:-local_mcp_ha}"  # Default per add-on locale

echo "🔄 Forzando update check per add-on: $ADDON_SLUG"
echo "📍 Home Assistant: http://$HA_HOST:8123"

# 1. Controlla versione attuale
echo ""
echo "1️⃣ Versione attuale installata:"
curl -s -X GET "http://$HA_HOST:8123/api/hassio/addons/$ADDON_SLUG/info" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" | jq -r '.data.version // "N/A"'

# 2. Refresh repository per forzare check aggiornamenti
echo ""
echo "2️⃣ Refresh repository..."
curl -s -X POST "http://$HA_HOST:8123/api/hassio/supervisor/reload" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json"

sleep 2

# 3. Controlla se c'è aggiornamento disponibile
echo ""
echo "3️⃣ Controllo aggiornamenti disponibili:"
UPDATE_AVAILABLE=$(curl -s -X GET "http://$HA_HOST:8123/api/hassio/addons/$ADDON_SLUG/info" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" | jq -r '.data.update_available // false')

if [ "$UPDATE_AVAILABLE" = "true" ]; then
    LATEST_VERSION=$(curl -s -X GET "http://$HA_HOST:8123/api/hassio/addons/$ADDON_SLUG/info" \
      -H "Authorization: Bearer $HA_TOKEN" \
      -H "Content-Type: application/json" | jq -r '.data.version_latest // "N/A"')
    
    echo "✅ Aggiornamento disponibile: $LATEST_VERSION"
    echo ""
    read -p "🚀 Vuoi aggiornare ora? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Aggiornamento in corso..."
        curl -s -X POST "http://$HA_HOST:8123/api/hassio/addons/$ADDON_SLUG/update" \
          -H "Authorization: Bearer $HA_TOKEN" \
          -H "Content-Type: application/json"
        
        echo ""
        echo "✅ Aggiornamento avviato!"
        echo "📋 Controlla i log: Add-ons → MCP Server → Log"
    else
        echo "⏭️  Aggiornamento saltato"
    fi
else
    echo "ℹ️  Nessun aggiornamento disponibile"
    echo ""
    echo "💡 Suggerimenti:"
    echo "   - Verifica che il push su GitHub sia completato"
    echo "   - Controlla GitHub Actions: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
    echo "   - Verifica che l'immagine sia pubblica: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | cut -d'/' -f1)?tab=packages"
    echo "   - Aspetta 1-2 minuti dopo il completamento del workflow"
fi
