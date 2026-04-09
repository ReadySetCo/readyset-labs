# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public GitHub issue**
2. Contact the maintainer directly with subject "Security: Brand Intelligence Scraper"
3. Include: description, reproduction steps, potential impact

We will respond within 48 hours and work on a fix.

---

## Known Security Considerations

### API Key Management

- **Never commit API keys** — Always use `.env` files (excluded via `.gitignore`)
- Rotate keys immediately if accidentally exposed
- Use scoped API keys with minimal permissions:
  - **OpenAI:** Use project-scoped service accounts
  - **Apify:** Use tokens with read-only actor access
  - **Firecrawl:** Standard API key

### Pre-Push Checklist

Run this checklist before pushing to any remote:

- [ ] `.env` file is NOT tracked (`git status` should show it as untracked or not listed)
- [ ] No API keys in any committed file: `git log -p | grep -i "sk-\|apify_api\|fc-\|AIzaSy"`
- [ ] `backend/.gitignore` is UTF-8 encoded (not UTF-16)
- [ ] `facebook_cookies.txt` is excluded by `.gitignore`
- [ ] No database files (`*.db`) are tracked

### Network Security

- The image proxy endpoint (`/api/research/proxy-image`) fetches external URLs server-side — in production, restrict to trusted image domains (e.g., `*.fbcdn.net`)
- CORS origins should be explicitly listed — avoid wildcards
- The video serving endpoint validates paths to prevent directory traversal

### Authentication

The current version does not implement authentication. It is designed for:
- **Local development** (localhost)
- **Temporary sharing** (ngrok with short-lived tunnels)

For production deployment, add authentication middleware before exposing to the internet.

---

## Supported Versions

| Version | Supported |
|---|---|
| 1.x | ✅ |
