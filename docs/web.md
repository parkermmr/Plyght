# Web

`pip install "plyght[web]"`

`plyght.web` gives every service the same FastAPI setup. The service
itself only writes its settings, lifespan and routers.

```python
from fastapi import APIRouter, Depends
from plyght.web import Identity, WebSettings, create_app, require_groups, web_config


class Settings(WebSettings):
    model_config = web_config("NOTES")
    name: str = "notes"
    version: str = "1.0.0"


router = APIRouter()


@router.get("/me")
def me(identity: Identity = Depends(require_groups())) -> dict:
    return {"user": identity.user, "groups": identity.groups}


app = create_app(Settings(), lifespan=lifespan)
app.include_router(router, prefix=app.state.settings.api_prefix)
```

## What `create_app` wires

| Piece                       | Behaviour                                                                                 |
|-----------------------------|-------------------------------------------------------------------------------------------|
| `ProxiedClientMiddleware`   | sets `request.state.client_ip`, read from `X-Forwarded-For` only when `trust_forwarded`    |
| `RequestLoggingMiddleware`  | one line per request: method, path, status, ms, client, and `request.state.caller` if set   |
| `SecurityHeadersMiddleware` | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`; CSP and HSTS when configured |
| `IdentityMiddleware`        | `request.state.identity` from verified auth proxy headers                                  |
| CORS                        | only when `cors_origins` is set; a `*` origin never allows credentials                     |
| `/docs`, `/redoc`           | swagger and redoc from assets under `/static/plyght`: no CDN and no inline script          |
| `/health`                   | `{"status": "ok"}` while the process answers                                               |
| `/ready`                    | `ready`, or `degraded` when the optional `app.state.ready_check` reports a False dependency |

Logging is configured from `log_level` and `log_json`.

## Settings

| Field                | Default                  | Meaning                                                    |
|----------------------|--------------------------|------------------------------------------------------------|
| `name`, `version`    | `service`, `0.1.0`       | OpenAPI title and version                                   |
| `port`               | `8000`                   | for your own `uvicorn.run`                                  |
| `api_prefix`         | `/api/v1`                | where your routers mount                                    |
| `log_level`, `log_json` | `INFO`, `false`       | passed to `plyght.configure`                                |
| `auth_enabled`       | `false`                  | off: every caller is anonymous and group checks pass        |
| `header_user`, `header_email`, `header_groups` | `x-auth-request-*` | identity headers the proxy injects       |
| `auth_proxy_secret`  | empty                    | shared secret proving a request came through the proxy      |
| `auth_proxy_header`  | `x-auth-proxy-secret`    | header carrying that secret                                 |
| `trust_forwarded`    | `false`                  | honour `X-Forwarded-For`                                    |
| `forwarded_hops`     | `1`                      | how many trusted proxies sit in front                       |
| `hsts`               | `false`                  | send `Strict-Transport-Security`; only behind real TLS      |
| `csp`                | empty                    | `Content-Security-Policy` on every response                 |
| `csp_exempt`         | empty                    | comma separated path prefixes the policy skips              |
| `cors_origins`       | empty                    | comma separated allowed origins                             |

## Identity

Deploy behind oauth2-proxy or something equivalent. The proxy
authenticates users against your identity provider and injects
`x-auth-request-user`, `-email` and `-groups`.

Anything that can reach the application port directly could forge those
headers, so they are trusted only when the request also carries
`auth_proxy_secret` on `auth_proxy_header`, compared in constant time.
Without a secret the headers are trusted unverified. That mode depends
entirely on network isolation between the proxy and the app, and logs a
warning once.

`require_groups(*groups)` is a route dependency that returns the
caller's `Identity`. It raises 401 for an anonymous caller and 403 for a
caller outside every listed group. With no groups it only requires
authentication.

For websockets or anything outside the middleware, `trusts_headers` and
`parse_identity` from `plyght.web.middleware.identity` run the same
checks against any header lookup.

## Client address

Each proxy appends the address it received from to `X-Forwarded-For`,
so only the right-most entries are written by proxies you run. With
`trust_forwarded`, the client is the entry `forwarded_hops` places from
the right. Entries further left come from the client and are never
used.
