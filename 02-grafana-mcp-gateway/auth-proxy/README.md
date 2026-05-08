# Option B — mcp-auth-proxy + Dex + Grafana (Confidential Web App, stateful proxy)

## Architecture

```
MCP Client ──OAuth (no client_id needed)──► mcp-auth-proxy :8082
                             ├─ OIDC code flow (client secret) ──► Dex :5556
                             ├─ issues own session JWT (RSA key)
                             └─► mcp-grafana :8000
                                   └─ forwards Authorization header
                                         └─► Grafana :3000
                                               └─ auth.jwt validates vs
                                                  mcp-auth-proxy JWKS
```

**Key properties of Option B:**
- mcp-auth-proxy is a **confidential Web App** — it holds the OIDC client secret
  server-side; MCP client users need no `client_id`
- mcp-auth-proxy issues its **own session JWT** (signed with its RSA key);
  the original OIDC token never reaches Grafana
- Grafana's `auth.jwt` validates against mcp-auth-proxy's JWKS, not the OIDC provider
- mcp-auth-proxy is **stateful** — it maintains sessions (local memory or DB)

**Compared to Option A:**
- Option A uses a Native/Public PKCE client — MCP users need a `client_id`,
  Envoy is stateless, and Grafana validates the original OIDC token directly
- Option B requires no `client_id` on the MCP client side — the proxy is
  the only registered OAuth client

## Architecture

```
MCP Client ──OAuth──► mcp-auth-proxy :8082
                             ├─ OIDC code flow ──► Dex :5556
                             ├─ issues session JWT (own RSA key)
                             └─► mcp-grafana :8000
                                   └─ forwards Authorization header
                                         └─► Grafana :3000
                                               └─ auth.jwt validates vs
                                                  mcp-auth-proxy JWKS
```

## Quick start

```bash
# No .env needed — all secrets are static for local testing
docker compose up -d
```

Open http://localhost:8082/mcp in your MCP client — it will redirect
to Dex for login.

**Credentials:** `user@example.com` / `password`

## MCP client configuration

The MCP endpoint is `http://localhost:8082/mcp`. mcp-auth-proxy handles
the full OAuth flow — the client is redirected to Dex for login and
receives a session JWT back from mcp-auth-proxy.

Login credentials: `user@example.com` / `password`

---

### OpenCode

Add to your `opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "grafana": {
      "type": "remote",
      "url": "http://localhost:8082/mcp",
      "enabled": true
    }
  }
}
```

Then authenticate (opens browser → Dex login → mcp-auth-proxy issues session JWT):

```bash
opencode mcp auth grafana
```

---

### Claude Code

```bash
claude mcp add --transport http grafana http://localhost:8082/mcp
```

Claude Code follows the OAuth redirect to Dex automatically.
After login, mcp-auth-proxy issues a session JWT that Claude Code
stores and reuses for subsequent requests.

To verify the server is connected:

```bash
claude mcp get grafana
```

## Ports

| Port | Service |
|---|---|
| 3000 | Grafana UI |
| 5556 | Dex OIDC |
| 8082 | MCP entry point (mcp-auth-proxy) |
| 9090 | Prometheus (internal only) |

## Production note

`GF_AUTH_JWT_AUTO_SIGN_UP=true` is set here for local convenience.

In production, `auto_sign_up = false` is recommended — Grafana users must
exist before the JWT path works. Users are typically created on first login via
a browser SSO provider. The MCP JWT path then works for subsequent
requests because the account already exists.

## Production mapping

| Local | Production |
|---|---|
| Dex | Any OIDC provider (Keycloak, Auth0, Okta, Google, etc.) |
| mcp-auth-proxy | mcp-auth-proxy deployment behind your ingress |
| Grafana JWT JWKS | `http://<mcp-auth-proxy-service>/.well-known/jwks.json` |
| Session store | PostgreSQL or MySQL (`REPOSITORY_BACKEND=postgres/mysql`) |
