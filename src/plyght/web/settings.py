"""
Web application settings, pydantic-settings style.

WebSettings carries everything plyght.web wires for a service:
identity headers, security headers, CORS, logging, and where the
versioned API mounts. Services subclass it with their own prefix so
each application keeps its own environment namespace while sharing
one set of resources/.env files:

    class Settings(WebSettings):
        model_config = web_config("MYSERVICE")
        data: str = "./data"

    Settings()          # MYSERVICE_* variables, resources/.env aware
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from plyght.settings import SecretFileSource, env_files


def web_config(prefix: str) -> SettingsConfigDict:
    """
    The model_config for a service's settings class:
    web_config("MYSERVICE") maps fields to MYSERVICE_* variables with
    defaults from resources/.env (PROFILE overlays included).
    """
    return SettingsConfigDict(
        env_prefix=f"{prefix.upper().rstrip('_')}_",
        env_file=env_files(),
        extra="ignore",
    )


class WebSettings(BaseSettings):
    """
    Everything a plyght.web application can be tuned with. Auth
    fields assume an oauth2-proxy (or equivalent) in front injecting
    identity headers; auth_enabled=False is development mode where
    every request is anonymous and group checks pass open.

    auth_proxy_secret is the shared secret the trusted proxy injects on
    auth_proxy_header to prove a request came through it; identity
    headers are honored only on a constant time match. Empty trusts the
    headers unverified, which relies on network isolation and is logged
    as a warning.

    trust_forwarded honors X-Forwarded-For only when a proxy you run
    sits in front, and forwarded_hops counts those proxies: the client
    is the entry that many places from the right. hsts belongs only
    behind real TLS. csp is the Content-Security-Policy sent on every
    response (empty sends none), and csp_exempt lists comma separated
    path prefixes it skips. cors_origins is comma separated; empty
    installs no CORS middleware, and a wildcard never allows
    credentials.
    """

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """
        Every field can arrive from a mounted file via
        <PREFIX><FIELD>_FILE, beating the plain
        environment; explicit constructor values still win.
        """
        return (
            init_settings,
            SecretFileSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    name: str = "service"
    version: str = "0.1.0"
    port: int = 8000
    api_prefix: str = "/api/v1"

    log_level: str = "INFO"
    log_json: bool = False

    auth_enabled: bool = False
    header_user: str = "x-auth-request-user"
    header_email: str = "x-auth-request-email"
    header_groups: str = "x-auth-request-groups"
    auth_proxy_secret: str = ""
    auth_proxy_header: str = "x-auth-proxy-secret"
    trust_forwarded: bool = False
    forwarded_hops: int = 1
    hsts: bool = False
    csp: str = ""
    csp_exempt: str = ""

    cors_origins: str = ""
