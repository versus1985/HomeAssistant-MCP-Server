# Guida Deployment Automatico

## Setup Iniziale (da fare una volta sola)

### 1. Configurare GitHub Repository

1. **Abilita permessi workflow**:
   - Vai su: `Settings` → `Actions` → `General`
   - Scorri fino a "Workflow permissions"
   - Seleziona: **Read and write permissions**
   - Spunta: **Allow GitHub Actions to create and approve pull requests**
   - Clicca **Save**

2. **Verifica GitHub Container Registry**:
   - Il workflow usa `GITHUB_TOKEN` automaticamente
   - Nessuna configurazione aggiuntiva necessaria

### 2. Primo Push e Verifica

```bash
git add .
git commit -m "feat: setup CI/CD pipeline"
git push origin main
```

Verifica che il workflow parta:
- Vai su GitHub → `Actions`
- Dovresti vedere il workflow "Build and Push Docker Image" in esecuzione
- Attendi il completamento (2-5 minuti)

### 3. Rendere Pubblico il Package (opzionale)

Per permettere a chiunque di usare l'add-on:

1. Vai su: `https://github.com/<username>?tab=packages`
2. Clicca su `homeassistant-mcp-server`
3. `Package settings` (in basso a destra)
4. Scorri fino a "Danger Zone"
5. `Change visibility` → **Public**
6. Conferma

## Workflow di Sviluppo Quotidiano

### Sviluppo Standard con Auto-Deploy

```bash
# 1. Modifica il codice
vim mcp_ha/app/main.py

# 2. Incrementa versione (importante!)
vim mcp_ha/config.yaml  # es. 1.4.0 → 1.4.1

# 3. Aggiorna CHANGELOG
vim mcp_ha/CHANGELOG.md
# Aggiungi entry sotto ## [1.4.1] - YYYY-MM-DD

# 4. Commit e push
git add .
git commit -m "feat: add new tool xyz"
git push origin main

# 5. Attendi 2-5 minuti
# GitHub Actions:
# - Builda immagine multi-arch
# - Pusha su ghcr.io con tag 1.4.1 e latest
# - Crea release GitHub automatica

# 6. Home Assistant rileva aggiornamento
# Vai su Add-ons → MCP Server → vedrai "Update available"
```

### Commit senza Release (es. documentazione)

```bash
git commit -m "docs: update README [skip-release]"
git push origin main
```

Questo builderà l'immagine ma **non creerà una release GitHub**.

### Test Locale Prima del Deploy

```bash
# Build locale
cd mcp_ha
docker build -t mcp-ha-local:test .

# Test
docker run --rm -p 8099:8099 \
  -e HA_BASE_URL=http://homeassistant:8123 \
  mcp-ha-local:test

# Verifica health
curl http://localhost:8099/health

# Se OK, procedi con commit e push
```

## Gestione Versioni

### Semantic Versioning

Usa [SemVer](https://semver.org/lang/it/):

- **MAJOR** (1.x.x → 2.x.x): Breaking changes (rimozione tool, cambio API)
- **MINOR** (1.4.x → 1.5.0): Nuove features backward-compatible (nuovo tool)
- **PATCH** (1.4.0 → 1.4.1): Bug fix e miglioramenti minori

### Esempio Pratico

```bash
# Nuovo tool (minor)
vim mcp_ha/config.yaml  # 1.4.0 → 1.5.0

# Bug fix (patch)
vim mcp_ha/config.yaml  # 1.4.0 → 1.4.1

# Breaking change (major)
vim mcp_ha/config.yaml  # 1.4.0 → 2.0.0
```

## Verifica Deploy

### 1. Controllare GitHub Actions

```
GitHub → Actions → Build and Push Docker Image
```

Status attesi:
- ✅ Checkout repository
- ✅ Extract version from config.yaml
- ✅ Set up Docker Buildx
- ✅ Log in to GitHub Container Registry
- ✅ Build and push Docker image (3 arch)
- ✅ Create GitHub Release

### 2. Verificare il Package

```
GitHub → Packages → homeassistant-mcp-server
```

Dovresti vedere:
- Tag: `1.4.0`, `latest`
- Platforms: `linux/amd64`, `linux/arm64`, `linux/arm/v7`
- Size: ~200-300 MB totali

### 3. Verificare la Release

```
GitHub → Releases
```

Dovresti vedere:
- Tag: `v1.4.0`
- Titolo: `Release v1.4.0`
- Asset: Link all'immagine Docker
- Note: Changelog automatico

### 4. Aggiornare in Home Assistant

1. Vai su **Add-ons** → **MCP Server for Home Assistant**
2. Dovresti vedere banner: **Update available: 1.4.0**
3. Clicca **Update**
4. Attendi download e riavvio automatico
5. Verifica nei log: versione aggiornata

## Troubleshooting

### Il workflow fallisce

**Errore: "Permission denied"**
```
Verifica Settings → Actions → Workflow permissions
Deve essere "Read and write permissions"
```

**Errore: "version not found"**
```
Verifica che mcp_ha/config.yaml contenga:
version: "x.y.z"
```

**Errore: "docker build failed"**
```
Testa localmente:
cd mcp_ha && docker build .
```

### Home Assistant non vede l'aggiornamento

1. **Controlla che config.yaml abbia il campo `image`**:
   ```yaml
   image: ghcr.io/{arch}/homeassistant-mcp-server
   ```

2. **Forza refresh manuale**:
   - Add-ons → Menu (3 punti) → "Check for updates"

3. **Verifica che l'immagine sia pubblica**:
   - GitHub → Packages → homeassistant-mcp-server
   - Visibility deve essere "Public"

### L'immagine è troppo grande

Le immagini multi-arch possono essere 200-300 MB in totale (normali per Python + dipendenze).

Per ridurre:
```dockerfile
# In Dockerfile, usa multi-stage build
FROM python:3.12-slim as builder
# ... installa dipendenze

FROM python:3.12-slim
COPY --from=builder /usr/local /usr/local
```

## Tips & Best Practices

### 1. Branch Protection

Proteggi il branch `main` per evitare deploy accidentali:
```
Settings → Branches → Add rule
- Branch name: main
- Require pull request before merging
- Require status checks (workflow deve passare)
```

### 2. Versioning Automatico (opzionale)

Per automatizzare l'increment della versione, aggiungi al workflow:
```yaml
- name: Bump version
  run: |
    # Script che incrementa automaticamente config.yaml
```

### 3. Notifiche Deploy

Ricevi notifiche Telegram/Discord quando il deploy completa:
```yaml
- name: Notify deployment
  if: success()
  run: |
    curl -X POST https://api.telegram.org/bot${{ secrets.TELEGRAM_TOKEN }}/sendMessage \
      -d chat_id=${{ secrets.TELEGRAM_CHAT_ID }} \
      -d text="🚀 MCP Server v${{ steps.version.outputs.version }} deployed!"
```

### 4. Staging Environment

Per testare prima della prod, usa branch diversi:
```yaml
on:
  push:
    branches:
      - main    # production
      - staging # test
```

## Rollback

Se un deploy introduce un bug:

### Metodo 1: Revert del Commit

```bash
git revert HEAD
git push origin main
# Trigger automaticamente un nuovo deploy
```

### Metodo 2: Rollback Manuale in HA

1. Add-ons → MCP Server
2. Configuration → Version
3. Seleziona versione precedente
4. Clicca "Install"

### Metodo 3: Eliminare Release e Tag

```bash
# Elimina tag localmente
git tag -d v1.4.0

# Elimina tag su GitHub
git push origin :refs/tags/v1.4.0

# Elimina release da GitHub UI
# Releases → v1.4.0 → Delete release
```

Poi rigenera con versione corretta.
