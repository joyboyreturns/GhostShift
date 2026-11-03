#!/usr/bin/env python3
"""Exercise production images with disposable loopback-only Docker data, never private seeds."""

import argparse
import http.cookiejar
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", default=os.getenv("DOCKER_CONTEXT"))
    parser.add_argument("--port", type=int, default=4180)
    parser.add_argument(
        "--report", type=Path, default=ROOT / "artifacts/container-validation.json"
    )
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose an unprivileged loopback port.")
    origin = f"http://127.0.0.1:{args.port}"
    environment = dict(os.environ)
    if args.context:
        environment["DOCKER_CONTEXT"] = args.context
    environment.update(
        DEMO_DOMAIN="localhost", PUBLIC_DEMO_SECRET=secrets.token_urlsafe(48)
    )
    compose = (
        ["docker-compose"] if shutil.which("docker-compose") else ["docker", "compose"]
    )
    project = "ghostshift-verify-" + secrets.token_hex(4)
    report = {
        "origin": origin,
        "project": project,
        "checks": [],
        "public_tls_verified": False,
    }
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def run(command, capture=False):
        return subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        ).stdout

    def check(name, condition):
        if not condition:
            raise RuntimeError(f"Failed: {name}")
        report["checks"].append(name)
        print(f"PASS: {name}", flush=True)

    def request(path, data=None, headers=None, opener=client):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(
            origin + path,
            data=body,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            with opener.open(req, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def healthy():
        deadline = time.monotonic() + 100
        last_error = "No successful response yet"
        while time.monotonic() < deadline:
            try:
                status = request("/api/health")[0]
                if status == 200:
                    return
                last_error = f"HTTP {status}"
            except (OSError, ValueError) as error:
                last_error = str(error)
            time.sleep(1)
        raise RuntimeError(f"Container health did not become ready: {last_error}")

    with tempfile.TemporaryDirectory(prefix="ghostshift-runtime-") as directory:
        config = Path(directory) / "compose.json"
        normalized = json.loads(
            run(
                compose
                + [
                    "--profile",
                    "maintenance",
                    "-f",
                    "deploy/compose.public.yml",
                    "config",
                    "--format",
                    "json",
                ],
                True,
            )
        )
        normalized.pop("name", None)
        for volume in normalized["volumes"].values():
            volume.pop("name", None)
        for network in normalized.get("networks", {}).values():
            network.pop("name", None)
        normalized["services"]["api"]["environment"].update(
            {
                "PUBLIC_ORIGIN": origin,
                "PUBLIC_COOKIE_SECURE": "false",
                "PUBLIC_TTL_SECONDS": "60",
                "PUBLIC_NEW_WORKSPACES_PER_HOUR": "200",
                "PUBLIC_WRITES_PER_MINUTE": "100",
            }
        )
        normalized["services"]["web"]["image"] = "ghostshift-web:validation"
        normalized["services"]["web"]["environment"]["GHOSTSHIFT_SITE"] = origin
        normalized["services"]["web"]["ports"] = [
            {
                "target": args.port,
                "published": str(args.port),
                "host_ip": "127.0.0.1",
                "protocol": "tcp",
            }
        ]
        config.write_text(json.dumps(normalized))
        config.chmod(0o600)
        base = compose + ["-p", project, "-f", str(config)]
        try:
            report["docker_version"] = run(
                ["docker", "version", "--format", "{{.Server.Version}}"], True
            ).strip()
            run(base + ["build", "api", "web"])
            run(base + ["run", "--rm", "prepare"])
            run(base + ["up", "-d", "--wait", "--wait-timeout", "100"])
            healthy()
            check("production images start with clean explicitly prepared data", True)
            environment["GHOSTSHIFT_CONTAINER_ORIGIN"] = origin
            run(
                [
                    "npm",
                    "--prefix",
                    "apps/web",
                    "exec",
                    "--",
                    "playwright",
                    "test",
                    "--config",
                    str(ROOT / "apps/web/playwright.container.config.ts"),
                ]
            )
            check("production-image browser journey and visitor isolation", True)
            status, _ = request("/api/demo")
            check("new temporary workspace created", status == 200)
            cookie = next(iter(jar))
            token = cookie.value
            expires = int(token.split(".")[0])
            status, source = request(
                "/api/documents",
                {
                    "title": "Fictional container persistence check",
                    "content": "This is disposable fictional validation data.",
                },
            )
            check("fictional write persists", status == 201)
            status, session = request(
                "/api/sessions",
                {"scenario_id": "night-market", "allow_draft_rehearsal": True},
            )
            check("real session created", status == 201)
            session_id = session["id"]
            run(base + ["restart", "api", "web"])
            run(base + ["up", "-d", "--wait", "--wait-timeout", "100"])
            healthy()
            check(
                "document survives API and Caddy restart",
                request(f"/api/documents/{source['id']}")[1] == source,
            )
            check(
                "session survives restart unchanged",
                request(f"/api/sessions/{session_id}")[1] == session,
            )
            containers = [
                json.loads(line)
                for line in run(base + ["ps", "--format", "json"], True).splitlines()
                if line
            ]
            report["containers"] = [
                {key: row.get(key) for key in ["Service", "Image", "State", "Health"]}
                for row in containers
            ]
            report["images"] = json.loads(
                run(base + ["images", "--format", "json"], True)
            )
            print(
                "Waiting for the allowed 60-second test workspace expiry…", flush=True
            )
            while time.time() <= expires + 1:
                time.sleep(1)
            old_cookie = {"Cookie": f"{cookie.name}={token}"}
            isolated = urllib.request.build_opener()
            status, _ = request(
                f"/api/documents/{source['id']}", headers=old_cookie, opener=isolated
            )
            check("expired workspace token rejected", status == 410)
            run(
                base
                + [
                    "exec",
                    "-T",
                    "api",
                    ".venv/bin/python",
                    "-m",
                    "app.services.demo_admin",
                    "cleanup",
                ]
            )
            count = run(
                base
                + [
                    "exec",
                    "-T",
                    "api",
                    ".venv/bin/python",
                    "-c",
                    "from pathlib import Path; print(len(list(Path('/data/workspaces').glob('*.db'))))",
                ],
                True,
            )
            check(
                "expired workspace database removed by maintenance",
                count.strip() == "0",
            )
            report["result"] = "passed"
        except Exception as error:
            report["result"] = "failed"
            report["error"] = str(error)
            raise
        finally:
            report["checked_at_utc"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n")
            run(base + ["down", "--volumes", "--remove-orphans"])
            print(f"Evidence: {args.report}", flush=True)


if __name__ == "__main__":
    main()
