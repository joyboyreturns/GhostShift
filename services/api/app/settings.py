"""Fail-closed public-demo configuration; local development stays on its existing database."""

import ipaddress
import os
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    public_demo: bool = False
    secret: str = Field(default="", repr=False)
    origin: str = ""
    template: Path = Path("data/demo-template.db")
    workspace_root: Path = Path("data/workspaces")
    ttl_seconds: int = Field(default=86400, ge=60, le=604800)
    max_workspaces: int = Field(default=200, ge=1, le=10000)
    workspace_bytes: int = Field(default=16 * 1024 * 1024, ge=1024 * 1024, le=128 * 1024 * 1024)
    body_bytes: int = Field(default=512 * 1024, ge=1024, le=2 * 1024 * 1024)
    body_timeout: float = Field(default=15, gt=0, le=60)
    writes_per_minute: int = Field(default=30, ge=1, le=1000)
    reads_per_minute: int = Field(default=240, ge=1, le=10000)
    new_workspaces_per_hour: int = Field(default=5, ge=1, le=200)
    cookie_secure: bool = True

    @model_validator(mode="after")
    def public_requirements(self) -> Self:
        if not self.public_demo:
            return self
        if len(self.secret) < 32 or self.secret.lower().startswith(
            ("change", "replace", "example")
        ):
            raise ValueError(
                "PUBLIC_DEMO_SECRET must be a generated secret of at least 32 characters"
            )
        parsed = urlsplit(self.origin)
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.scheme not in {"http", "https"}
        ):
            raise ValueError("PUBLIC_ORIGIN must be a single origin without a trailing slash")
        if not self.cookie_secure:
            try:
                loopback = ipaddress.ip_address(parsed.hostname).is_loopback
            except ValueError:
                loopback = parsed.hostname == "localhost"
            if not loopback or parsed.scheme != "http":
                raise ValueError(
                    "Insecure cookies are allowed only for explicit HTTP loopback testing"
                )
        elif parsed.scheme != "https":
            raise ValueError("Public demo requires HTTPS")
        if self.template.resolve().is_relative_to(self.workspace_root.resolve()):
            raise ValueError("The clean template must be outside the workspace directory")
        if os.getenv("WEB_CONCURRENCY", "1") != "1":
            raise ValueError("Public demo limits require one API worker")
        return self

    @property
    def cookie_name(self) -> str:
        return "__Host-ghostshift" if self.cookie_secure else "ghostshift_loopback_demo"

    @classmethod
    def from_env(cls) -> Self:
        names = {
            "secret": "PUBLIC_DEMO_SECRET",
            "origin": "PUBLIC_ORIGIN",
            "template": "PUBLIC_TEMPLATE_PATH",
            "workspace_root": "PUBLIC_WORKSPACE_ROOT",
            "ttl_seconds": "PUBLIC_TTL_SECONDS",
            "max_workspaces": "PUBLIC_MAX_WORKSPACES",
            "workspace_bytes": "PUBLIC_WORKSPACE_BYTES",
            "body_bytes": "MAX_BODY_BYTES",
            "body_timeout": "BODY_TIMEOUT_SECONDS",
            "writes_per_minute": "PUBLIC_WRITES_PER_MINUTE",
            "reads_per_minute": "PUBLIC_READS_PER_MINUTE",
            "new_workspaces_per_hour": "PUBLIC_NEW_WORKSPACES_PER_HOUR",
        }
        values = {key: os.environ[name] for key, name in names.items() if name in os.environ}
        return cls.model_validate(
            {
                **values,
                "public_demo": os.getenv("PUBLIC_DEMO", "false"),
                "cookie_secure": os.getenv("PUBLIC_COOKIE_SECURE", "true"),
            }
        )
