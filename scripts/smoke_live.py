#!/usr/bin/env python3
"""Acceptance smoke test for a running GhostShift deployment (standard library only).

Usage: python3 scripts/smoke_live.py https://demo.example.com [--insecure-http]

Checks only what can be observed over HTTP. It does NOT prove TLS issuance, DNS, firewall
or 24-hour expiry behavior; verify those on the host (docs/DEPLOYMENT.md). It creates temporary
fictional-demo workspaces and never sends real documents.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request
from typing import Any

SECURITY_HEADERS = (
    "x-content-type-options",
    "x-frame-options",
    "content-security-policy",
    "referrer-policy",
)


class Client:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any, Any]:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            self.base + path, data=data, method=method, headers={"Content-Type": "application/json"}
        )
        try:
            with self.opener.open(req, timeout=20) as resp:
                return resp.status, resp.headers, resp.read().decode(errors="replace")
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read().decode(errors="replace")

    def json(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        status, _, text = self.request(method, path, body)
        try:
            return status, json.loads(text)
        except json.JSONDecodeError:
            return status, text


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        print(("PASS " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
        if not ok:
            self.failures.append(name)


def run(base: str, allow_http: bool) -> int:
    report = Report()
    https = base.startswith("https://")
    report.check("uses https", https or allow_http, "pass --insecure-http only for local staging")

    one, two = Client(base), Client(base)
    status, payload = one.json("GET", "/api/health")
    report.check("health ok", status == 200 and isinstance(payload, dict) and payload.get("status") == "ok")

    status, headers, html = one.request("GET", "/")
    report.check("SPA root serves HTML", status == 200 and "<div id=\"root\"" in html)
    missing = [h for h in SECURITY_HEADERS if headers is None or headers.get(h) is None]
    report.check("security headers present", not missing, f"missing {missing}")
    status, _, deep = one.request("GET", "/simulation/does-not-exist")
    report.check("deep link falls back to SPA", status == 200 and "<div id=\"root\"" in deep)

    # Allocate an isolated workspace for each client via the validated reset route.
    for label, client in (("A", one), ("B", two)):
        status, payload = client.json("POST", "/api/demo/reset", {})
        report.check(f"workspace {label} allocated", status in (200, 201) and isinstance(payload, dict))
    cookie_flags = [
        (c.name, c.secure, c.has_nonstandard_attr("HttpOnly"))
        for c in one.jar
    ]
    report.check("workspace cookie issued", bool(cookie_flags))
    if https and cookie_flags:
        report.check("cookie is Secure and HttpOnly", all(s and h for _, s, h in cookie_flags))

    status, catalog = one.json("GET", "/api/demo")
    demos = catalog.get("demos", []) if isinstance(catalog, dict) else []
    report.check("demo catalog lists fictional playbooks", status == 200 and len(demos) >= 1)
    if not demos:
        return 1
    scenario_id = demos[0]["scenario_id"]

    status, session = one.json("POST", "/api/sessions", {"scenario_id": scenario_id, "allow_draft_rehearsal": True})
    report.check("rehearsal starts", status == 201 and isinstance(session, dict) and "id" in session)
    if not (isinstance(session, dict) and "id" in session):
        return 1
    sid = session["id"]

    status, replay = one.json("GET", f"/api/sessions/{sid}/replay")
    report.check("replay verifies", status == 200 and isinstance(replay, dict) and replay.get("verified") is True)
    status, rep = one.json("GET", f"/api/sessions/{sid}/report")
    report.check("report available", status == 200 and isinstance(rep, dict))

    status, _ = two.json("GET", f"/api/sessions/{sid}")
    report.check("other workspace cannot read the session", status in (403, 404), f"got HTTP {status}")

    fresh = Client(base)
    status, _ = fresh.json("GET", f"/api/sessions/{sid}")
    report.check("cookie-less client is refused", status in (400, 401, 403, 404, 429), f"got HTTP {status}")

    print()
    if report.failures:
        print(f"{len(report.failures)} check(s) failed: {', '.join(report.failures)}")
        return 1
    print("All HTTP smoke checks passed. TLS issuance, DNS, firewall and expiry still need host verification.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--insecure-http", action="store_true", help="allow http:// for local staging")
    args = parser.parse_args()
    sys.exit(run(args.url, args.insecure_http))


if __name__ == "__main__":
    main()
