# Grafana MCP Auth — Local E2E Demo

Two self-contained Docker Compose stacks that demonstrate how to add
OAuth authentication in front of [mcp-grafana](https://github.com/grafana/mcp-grafana),
the official Grafana MCP server.

Each stack runs entirely locally — no external accounts, no cloud services.
A local [Dex](https://dexidp.io) instance replaces any real OIDC provider
(Okta, Auth0, Keycloak, Google, etc.).

> This repository accompanies a Medium post: [MCP is the New Internal API — Treat it Like One](https://medium.com/@paulojmdias/mcp-is-the-new-internal-api-treat-it-like-one-6b09028eb884)

---

## The Problem

[mcp-grafana](https://github.com/grafana/mcp-grafana) ships with no
authentication layer. Out of the box, anyone who can reach the MCP endpoint
can query your Grafana instance. In production you need to:

1. Ensure only authenticated users can call the MCP server
2. Decide whether Grafana sees a shared service account or per-user identity

These two stacks show two different answers to that question.

---

## Option A — Envoy gateway, Native PKCE client

**`gateway-native-pkce/`**

```
MCP Client ──PKCE (client_id, no secret)──► Dex :5556
MCP Client ──Bearer JWT──► Envoy :8080
                             ├─ validates JWT vs Dex JWKS (stateless)
                             ├─ sets X-User-Email header
                             └─► mcp-grafana :8000 (JWT forwarded)
                                     └─► Grafana :3000
                                           └─ auth.jwt validates vs Dex JWKS
```

**How it works:**
- The MCP client is registered as a **Native/Public OAuth app** — it has a
  `client_id` but no secret; PKCE is the proof of identity
- Envoy validates the JWT at the edge (stateless — no sessions, no DB)
- The original OIDC token flows all the way through to Grafana
- Grafana re-validates it independently via `auth.jwt` against Dex's JWKS
- Each user gets their own Grafana identity and a full audit trail

**What you need to configure on the MCP client side:**
- The MCP server URL: `http://localhost:8080/mcp`
- The OAuth `client_id`: `mcp-client` (pre-registered in Dex)
- No secret

**Production mapping:**
- Replace Dex with your OIDC provider (Okta, Auth0, Keycloak, etc.)
- Replace Envoy with any JWT-validating reverse proxy or service mesh sidecar
- Register a Native App in your OIDC provider and distribute the `client_id`
  to MCP client users

→ **[gateway-native-pkce/README.md](./gateway-native-pkce/README.md)**

---

## Option B — mcp-auth-proxy, Confidential Web App client

**`auth-proxy/`**

```
MCP Client ──OAuth (no client_id needed)──► mcp-auth-proxy :8082
                             ├─ OIDC code flow (client secret) ──► Dex :5556
                             ├─ issues own session JWT (RSA key)
                             └─► mcp-grafana :8000 (JWT forwarded)
                                     └─► Grafana :3000
                                           └─ auth.jwt validates vs
                                              mcp-auth-proxy JWKS
```

**How it works:**
- [mcp-auth-proxy](https://github.com/sigbit/mcp-auth-proxy) acts as a
  **confidential Web App** — it holds the OIDC client secret server-side
- MCP client users just point at `http://localhost:8082/mcp` — no `client_id`
  to distribute, no OAuth app registration on the user side
- mcp-auth-proxy manages the OIDC session and issues its own short-lived JWT
- Grafana validates that JWT against mcp-auth-proxy's JWKS endpoint
- Each user still gets their own Grafana identity

**What you need to configure on the MCP client side:**
- The MCP server URL: `http://localhost:8082/mcp`
- Nothing else — mcp-auth-proxy handles the full OAuth flow

**Production mapping:**
- Replace Dex with your OIDC provider
- Deploy mcp-auth-proxy behind your ingress with a real session store
  (`REPOSITORY_BACKEND=postgres` or `mysql`)
- No `client_id` distribution needed — one registration, all users

→ **[auth-proxy/README.md](./auth-proxy/README.md)**

---

## Comparison

| | Option A | Option B |
|---|---|---|
| OAuth client type | Native/Public (PKCE, no secret) | Confidential Web App (secret server-side) |
| MCP client setup | Needs `client_id` | Just a URL |
| Token in Grafana | Original OIDC JWT | mcp-auth-proxy session JWT |
| Grafana identity | Per-user | Per-user |
| Grafana JWKS source | OIDC provider directly | mcp-auth-proxy |
| Stateful component | None (Envoy is stateless) | mcp-auth-proxy (session store) |
| Scales horizontally | Yes — trivially | Requires shared session store |
| Suited for | Managed OIDC, power users, service meshes | Self-hosted, zero-config UX for users |

Both options give **per-user Grafana identity** and a full audit trail.
The choice comes down to where you want to manage state and how much
you want to expose to MCP client users.

---

## Quick start

Both stacks are zero-dependency — just Docker and Docker Compose v2.

```bash
# Option A
cd gateway-native-pkce
docker compose up -d

# Option B
cd auth-proxy
docker compose up -d
```

Default credentials for both: `user@example.com` / `password`

Grafana UI: `http://localhost:3000` — click **Sign in with Dex**

---

## Stack contents

Both stacks include:

| Service | Purpose |
|---|---|
| [Dex](https://dexidp.io) | Local OIDC provider — replaces any real IdP |
| [mcp-grafana](https://github.com/grafana/mcp-grafana) | Official Grafana MCP server |
| [Grafana](https://grafana.com) | Pre-configured with Prometheus datasource |
| [Prometheus](https://prometheus.io) | Scraping itself — real metric data for MCP tool demos |

Option A also includes **Envoy** and a **nginx well-known** container.
Option B replaces those with **mcp-auth-proxy**.

---

## Supported MCP clients

Both stacks work with any MCP client that supports OAuth 2.0.
Tested with:

- **[OpenCode](https://opencode.ai)** — see per-stack README for `opencode.jsonc` snippet
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** — see per-stack README for `claude mcp add` command

---

## Replacing Dex with a real OIDC provider

Dex is only used to make the stacks self-contained. Every component is
configured via standard OIDC — swapping Dex for a real provider is a
matter of changing a few URLs and credentials.

**Option A** — update `envoy.yaml`:
```yaml
issuer: "https://your-provider.example.com"
remote_jwks:
  http_uri:
    uri: "https://your-provider.example.com/.well-known/jwks.json"
```
And update `GF_AUTH_JWT_JWK_SET_URL` + `GF_AUTH_GENERIC_OAUTH_*` in `docker-compose.yml`.

**Option B** — update `docker-compose.yml`:
```yaml
OIDC_CONFIGURATION_URL: "https://your-provider.example.com/.well-known/openid-configuration"
OIDC_CLIENT_ID: "your-client-id"
OIDC_CLIENT_SECRET: "your-client-secret"
OIDC_ISSUER_URL: "https://your-provider.example.com"
```
And update `GF_AUTH_JWT_JWK_SET_URL` + `GF_AUTH_GENERIC_OAUTH_*` in `docker-compose.yml`.
