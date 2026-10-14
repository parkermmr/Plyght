"""
Self-hosted API docs: swagger-ui and redoc served from the static
bundle plyght ships, so the docs work on air-gapped and locked-down
networks (the default fastapi docs pull from a CDN). Nothing here
runs inline script, so the pages render under a script-src 'self'
content security policy.
"""

from html import escape

from fastapi import APIRouter, Request
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse

router = APIRouter(include_in_schema=False)

STATIC = "/static/plyght"

SWAGGER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="{static}/swagger-ui.css">
<link rel="shortcut icon" href="{static}/favicon.ico">
</head>
<body>
<div id="swagger-ui"></div>
<script src="{static}/swagger-ui-bundle.js"></script>
<script src="{static}/swagger-init.js" data-spec="{spec}" data-redirect="/docs/oauth2-redirect"></script>
</body>
</html>
"""


@router.get("/docs")
async def swagger_ui(request: Request):
    """Swagger UI from the vendored static bundle."""
    return HTMLResponse(
        SWAGGER.format(
            title=escape(f"{request.app.title} - Swagger UI"),
            static=STATIC,
            spec=escape(request.app.openapi_url),
        )
    )


@router.get("/docs/oauth2-redirect")
async def swagger_ui_redirect():
    """OAuth2 redirect helper for swagger UI flows."""
    return get_swagger_ui_oauth2_redirect_html()


@router.get("/redoc")
async def redoc(request: Request):
    """ReDoc from the vendored static bundle."""
    return get_redoc_html(
        openapi_url=request.app.openapi_url,
        title=f"{request.app.title} - ReDoc",
        redoc_js_url=f"{STATIC}/redoc.standalone.js",
        redoc_favicon_url=f"{STATIC}/favicon.ico",
        with_google_fonts=False,
    )
