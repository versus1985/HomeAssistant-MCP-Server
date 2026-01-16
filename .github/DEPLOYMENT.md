# Automated Deployment Guide

## Initial Setup (one-time only)

### 1. Configure GitHub Repository

1. **Enable workflow permissions**:
   - Go to: `Settings` → `Actions` → `General`
   - Scroll to "Workflow permissions"
   - Select: **Read and write permissions**
   - Check: **Allow GitHub Actions to create and approve pull requests**
   - Click **Save**

2. **Verify GitHub Container Registry**:
   - The workflow uses `GITHUB_TOKEN` automatically
   - No additional configuration needed

### 2. First Push and Verification

```bash
git add .
git commit -m "feat: setup CI/CD pipeline"
git push origin main
```

Verify the workflow starts:
- Go to GitHub → `Actions`
- You should see the "Build and Push Docker Image" workflow running
- Wait for completion (2-5 minutes)

### 3. Make the Package Public (optional)

To allow anyone to use the add-on:

1. Go to: `https://github.com/<username>?tab=packages`
2. Click on `homeassistant-mcp-server`
3. `Package settings` (bottom right)
4. Scroll to "Danger Zone"
5. `Change visibility` → **Public**
6. Confirm

## Daily Development Workflow

### Standard Development with Auto-Deploy

```bash
# 1. Modify the code
vim mcp_ha/app/main.py

# 2. Increment version (important!)
vim mcp_ha/config.yaml  # e.g., 1.4.0 → 1.4.1

# 3. Update CHANGELOG
vim mcp_ha/CHANGELOG.md
# Add entry under ## [1.4.1] - YYYY-MM-DD

# 4. Commit and push
git add .
git commit -m "feat: add new tool xyz"
git push origin main

# 5. Wait 2-5 minutes
# GitHub Actions:
# - Builds multi-arch image
# - Pushes to ghcr.io with tags 1.4.1 and latest
# - Creates automatic GitHub release

# 6. Home Assistant detects update
# Go to Add-ons → MCP Server → you'll see "Update available"
```

### Commit without Release (e.g., documentation)

```bash
git commit -m "docs: update README [skip-release]"
git push origin main
```

This will build the image but **won't create a GitHub release**.

### Local Testing Before Deploy

```bash
# Local build
cd mcp_ha
docker build -t mcp-ha-local:test .

# Test
docker run --rm -p 8099:8099 \
  -e HA_BASE_URL=http://homeassistant:8123 \
  mcp-ha-local:test

# Verify health
curl http://localhost:8099/health

# If OK, proceed with commit and push
```

## Version Management

### Semantic Versioning

Use [SemVer](https://semver.org/):

- **MAJOR** (1.x.x → 2.x.x): Breaking changes (tool removal, API change)
- **MINOR** (1.4.x → 1.5.0): New backward-compatible features (new tool)
- **PATCH** (1.4.0 → 1.4.1): Bug fixes and minor improvements

### Practical Example

```bash
# New tool (minor)
vim mcp_ha/config.yaml  # 1.4.0 → 1.5.0

# Bug fix (patch)
vim mcp_ha/config.yaml  # 1.4.0 → 1.4.1

# Breaking change (major)
vim mcp_ha/config.yaml  # 1.4.0 → 2.0.0
```

## Deploy Verification

### 1. Check GitHub Actions

```
GitHub → Actions → Build and Push Docker Image
```

Expected statuses:
- ✅ Checkout repository
- ✅ Extract version from config.yaml
- ✅ Set up Docker Buildx
- ✅ Log in to GitHub Container Registry
- ✅ Build and push Docker image (3 arch)
- ✅ Create GitHub Release

### 2. Verify the Package

```
GitHub → Packages → homeassistant-mcp-server
```

You should see:
- Tags: `1.4.0`, `latest`
- Platforms: `linux/amd64`, `linux/arm64`, `linux/arm/v7`
- Size: ~200-300 MB total

### 3. Verify the Release

```
GitHub → Releases
```

You should see:
- Tag: `v1.4.0`
- Title: `Release v1.4.0`
- Asset: Link to Docker image
- Notes: Automatic changelog

### 4. Update in Home Assistant

1. Go to **Add-ons** → **MCP Server for Home Assistant**
2. You should see banner: **Update available: 1.4.0**
3. Click **Update**
4. Wait for download and automatic restart
5. Check logs: updated version

## Troubleshooting

### Workflow fails

**Error: "Permission denied"**
```
Check Settings → Actions → Workflow permissions
Must be "Read and write permissions"
```

**Error: "version not found"**
```
Verify that mcp_ha/config.yaml contains:
version: "x.y.z"
```

**Error: "docker build failed"**
```
Test locally:
cd mcp_ha && docker build .
```

### Home Assistant doesn't see the update

1. **Check that config.yaml has the `image` field**:
   ```yaml
   image: ghcr.io/{arch}/homeassistant-mcp-server
   ```

2. **Force manual refresh**:
   - Add-ons → Menu (3 dots) → "Check for updates"

3. **Verify the image is public**:
   - GitHub → Packages → homeassistant-mcp-server
   - Visibility must be "Public"

### Image is too large

Multi-arch images can be 200-300 MB total (normal for Python + dependencies).

To reduce:
```dockerfile
# In Dockerfile, use multi-stage build
FROM python:3.12-slim as builder
# ... install dependencies

FROM python:3.12-slim
COPY --from=builder /usr/local /usr/local
```

## Tips & Best Practices

### 1. Branch Protection

Protect the `main` branch to avoid accidental deploys:
```
Settings → Branches → Add rule
- Branch name: main
- Require pull request before merging
- Require status checks (workflow must pass)
```

### 2. Automatic Versioning (optional)

To automate version incrementing, add to workflow:
```yaml
- name: Bump version
  run: |
    # Script that automatically increments config.yaml
```

### 3. Deploy Notifications

Receive Telegram/Discord notifications when deploy completes:
```yaml
- name: Notify deployment
  if: success()
  run: |
    curl -X POST https://api.telegram.org/bot${{ secrets.TELEGRAM_TOKEN }}/sendMessage \
      -d chat_id=${{ secrets.TELEGRAM_CHAT_ID }} \
      -d text="🚀 MCP Server v${{ steps.version.outputs.version }} deployed!"
```

### 4. Staging Environment

To test before production, use different branches:
```yaml
on:
  push:
    branches:
      - main    # production
      - staging # test
```

## Rollback

If a deploy introduces a bug:

### Method 1: Revert the Commit

```bash
git revert HEAD
git push origin main
# Automatically triggers a new deploy
```

### Method 2: Manual Rollback in HA

1. Add-ons → MCP Server
2. Configuration → Version
3. Select previous version
4. Click "Install"

### Method 3: Delete Release and Tag

```bash
# Delete tag locally
git tag -d v1.4.0

# Delete tag on GitHub
git push origin :refs/tags/v1.4.0

# Delete release from GitHub UI
# Releases → v1.4.0 → Delete release
```

Then regenerate with correct version.
