# Script PowerShell per forzare l'aggiornamento dell'add-on MCP Server in Home Assistant
# Uso: .\force-update.ps1 -HAHost "192.168.1.100" -HAToken "eyJhbGc..."

param(
    [Parameter(Mandatory=$true)]
    [string]$HAHost,
    
    [Parameter(Mandatory=$true)]
    [string]$HAToken,
    
    [Parameter(Mandatory=$false)]
    [string]$AddonSlug = "local_mcp_ha"
)

$ErrorActionPreference = "Stop"
$BaseUrl = "http://${HAHost}:8123/api/hassio"
$Headers = @{
    "Authorization" = "Bearer $HAToken"
    "Content-Type" = "application/json"
}

Write-Host "🔄 Forzando update check per add-on: $AddonSlug" -ForegroundColor Cyan
Write-Host "📍 Home Assistant: http://${HAHost}:8123" -ForegroundColor Gray
Write-Host ""

# 1. Controlla versione attuale
Write-Host "1️⃣ Versione attuale installata:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/addons/$AddonSlug/info" -Headers $Headers -Method Get
    $currentVersion = $response.data.version
    Write-Host "   $currentVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Errore nel recuperare info add-on" -ForegroundColor Red
    Write-Host "   Verifica che l'add-on sia installato e che il token sia valido" -ForegroundColor Gray
    exit 1
}

# 2. Refresh repository
Write-Host ""
Write-Host "2️⃣ Refresh repository..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri "$BaseUrl/supervisor/reload" -Headers $Headers -Method Post | Out-Null
    Write-Host "   ✅ Repository aggiornato" -ForegroundColor Green
    Start-Sleep -Seconds 2
} catch {
    Write-Host "   ⚠️ Errore nel refresh (continuo comunque...)" -ForegroundColor Yellow
}

# 3. Controlla aggiornamenti
Write-Host ""
Write-Host "3️⃣ Controllo aggiornamenti disponibili:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/addons/$AddonSlug/info" -Headers $Headers -Method Get
    $updateAvailable = $response.data.update_available
    $latestVersion = $response.data.version_latest
    
    if ($updateAvailable -eq $true) {
        Write-Host "   ✅ Aggiornamento disponibile: $latestVersion" -ForegroundColor Green
        Write-Host ""
        
        $confirmation = Read-Host "🚀 Vuoi aggiornare ora? (y/n)"
        
        if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
            Write-Host ""
            Write-Host "📦 Aggiornamento in corso..." -ForegroundColor Cyan
            
            Invoke-RestMethod -Uri "$BaseUrl/addons/$AddonSlug/update" -Headers $Headers -Method Post | Out-Null
            
            Write-Host ""
            Write-Host "✅ Aggiornamento avviato!" -ForegroundColor Green
            Write-Host "📋 Controlla i log: Add-ons → MCP Server → Log" -ForegroundColor Gray
        } else {
            Write-Host "⏭️  Aggiornamento saltato" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ℹ️  Nessun aggiornamento disponibile" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "💡 Suggerimenti:" -ForegroundColor Cyan
        Write-Host "   - Verifica che il push su GitHub sia completato" -ForegroundColor Gray
        Write-Host "   - Controlla GitHub Actions nella tab Actions del repository" -ForegroundColor Gray
        Write-Host "   - Verifica che l'immagine sia pubblica in GitHub Packages" -ForegroundColor Gray
        Write-Host "   - Aspetta 1-2 minuti dopo il completamento del workflow" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Errore nel controllo aggiornamenti" -ForegroundColor Red
    Write-Host "   $_" -ForegroundColor Gray
    exit 1
}
