# Option A — Envoy + Dex + Grafana (Native PKCE client, stateless gateway)

## Architecture

```
MCP Client ──PKCE (client_id, no secret)──► Dex :5556
MCP Client ──Bearer JWT──► Envoy :8080
                             ├─ validates JWT vs Dex JWKS (stateless)
                             ├─ sets X-User-Email from token claim
                             └─► mcp-grafana :8000 (JWT forwarded)
                                     └─► Grafana :3000
                                           └─ auth.jwt validates vs Dex JWKS
```

**Key properties of Option A:**
- The MCP client is a **Native/Public OAuth app** — it has a `client_id` but no secret
- PKCE is the proof of identity (no secret ever leaves the client)
- Envoy is **stateless** — it only validates the JWT signature, no sessions
- The original OIDC token flows all the way to Grafana unmodified
- In production: an admin registers one Native App in the OIDC provider and
  distributes the `client_id` to all MCP client users

**Compared to Option B:**
- Option B uses a **confidential Web App** client with a server-side secret
- mcp-auth-proxy manages the OIDC session and issues its own JWT
- MCP client users need no `client_id` — they just hit the proxy URL
- Option B is stateful (session store); Option A is fully stateless

| | Option A | Option B |
|---|---|---|
| OAuth client type | Native/Public (PKCE, no secret) | Confidential Web App (secret server-side) |
| Token in Grafana | Original OIDC JWT from Dex | mcp-auth-proxy session JWT |
| MCP client needs `client_id` | Yes — distributed by admin | No — proxy is the only client |
| Stateful component | None | mcp-auth-proxy (session store) |
| JWKS in Grafana | Points at Dex directly | Points at mcp-auth-proxy |

## Quick start

```bash
cp .env.example .env
docker compose up -d
```

Open `http://localhost:3000` and click **Sign in with Dex** to log in as
`user@example.com` / `password`.

## MCP client configuration

The MCP endpoint is `http://localhost:8080/mcp`. The client discovers the
authorization server automatically via
`http://localhost:8080/.well-known/oauth-protected-resource`.

Login credentials: `user@example.com` / `password`

> In Option A the MCP client must present the pre-registered `client_id`
> (`mcp-client` for local Dex). In production, an admin registers a Native App
> in the OIDC provider and distributes the `client_id` to users — no secret needed.

---

### OpenCode

Add to your `opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "grafana": {
      "type": "remote",
      "url": "http://localhost:8080/mcp",
      "enabled": true,
      "oauth": {
        "clientId": "mcp-client"
      }
    }
  }
}
```

Then authenticate (triggers the browser PKCE flow against Dex):

```bash
opencode mcp auth grafana
```

---

### Claude Code

```bash
claude mcp add --transport http \
  --client-id mcp-client \
  --callback-port 19876 \
  grafana http://localhost:8080/mcp
```

`--client-id` tells Claude Code to use the pre-registered Native App client.
`--callback-port 19876` must match the redirect URI registered in Dex
(`http://localhost:19876/mcp/oauth/callback` in `dex-config.yaml`).

To verify the server is connected:

```bash
claude mcp get grafana
```

## Ports

| Port | Service |
|---|---|
| 3000 | Grafana UI |
| 5556 | Dex OIDC |
| 8080 | MCP entry point (Envoy) |
| 9090 | Prometheus (internal only) |
| 9901 | Envoy admin UI |

## Production mapping

| Local | Production |
|---|---|
| Dex | Any OIDC provider (Keycloak, Auth0, Okta, Google, etc.) |
| `mcp-client` client_id | Native App registered in your OIDC provider |
| Envoy container | Any JWT-validating reverse proxy or service mesh |

To use a different OIDC provider: change `issuer` and `remote_jwks.http_uri`
in `envoy.yaml`, update `GF_AUTH_JWT_JWK_SET_URL` and `GF_AUTH_GENERIC_OAUTH_*`
in `docker-compose.yml`, and register a new Native App in your provider.
