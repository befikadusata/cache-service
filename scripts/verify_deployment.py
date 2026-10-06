"""Verify an isolated Compose deployment; retain its volume for inspection."""

import json
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    project = f"cache-b18-{uuid4().hex[:12]}"
    environment = os.environ.copy()
    environment.update(DB_USER="cache", DB_NAME="cache", DB_PASS=secrets.token_hex(24))
    print(f"Verification project: {project}", flush=True)
    with tempfile.TemporaryDirectory(prefix="cache-b18-") as directory:
        temporary = Path(directory)
        override = temporary / "compose.yaml"
        override.write_text(
            'services:\n  database:\n    ports: !reset []\n'
            '  api:\n    ports: !override ["127.0.0.1::8000"]\n',
            encoding="utf-8",
        )
        compose = [
            "docker", "compose", "--project-name", project, "--env-file", "/dev/null",
            "-f", str(ROOT / "compose.yaml"), "-f", str(override),
        ]

        def run(*arguments: str, timeout: int = 120) -> str:
            result = subprocess.run(
                [*compose, *arguments], cwd=ROOT, env=environment,
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode:
                # Container diagnostics can contain credentials; do not echo them.
                raise RuntimeError(f"Compose {arguments[0]} failed (exit {result.returncode})")
            return result.stdout.strip()

        def check(condition: bool, description: str) -> None:
            if not condition:
                raise RuntimeError(description)
            print(f"PASS: {description}", flush=True)

        def address() -> str:
            return f"http://{run('port', 'api', '8000')}"

        def get(host: str, path: str) -> dict:
            with urlopen(f"{host}{path}", timeout=5) as response:
                return json.load(response)

        def ready(host: str) -> None:
            deadline = time.monotonic() + 60
            while True:
                try:
                    if get(host, "/health/ready") == {"status": "ok"}:
                        break
                except (URLError, OSError):
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("API readiness deadline exceeded")
                time.sleep(0.2)
            check(get(host, "/health/live") == {"status": "ok"}, "both health endpoints")

        def cli(payload: dict, repeat: int = 1) -> list[dict]:
            output = run(
                "exec", "-T", "api", "cache-service", "--host", "http://127.0.0.1:8000",
                "--json", json.dumps(payload), "--repeat", str(repeat),
            )
            return [json.loads(line) for line in output.splitlines()]

        def sql(query: str) -> str:
            return run(
                "exec", "-T", "database", "psql", "-U", "cache", "-d", "cache",
                "-At", "-c", query,
            )

        def cache_rows() -> str:
            return sql(
                "SELECT coalesce(json_agg(t ORDER BY source), '[]') FROM "
                "(SELECT version, encode(source_digest, 'hex') AS digest, source, result "
                "FROM transformations) t"
            )

        try:
            run("config", "--quiet")
            run("build", "--no-cache", timeout=600)
            print("PASS: clean Docker build", flush=True)
            run("up", "-d", timeout=180)
            host = address()
            ready(host)
            raw_services = run("ps", "--all", "--format", "json")
            # Compose versions emit either an array or newline-separated objects.
            services = (
                json.loads(raw_services) if raw_services.startswith("[")
                else [json.loads(line) for line in raw_services.splitlines()]
            )
            migration = next(service for service in services if service["Service"] == "migrate")
            check(
                migration["State"] == "exited" and migration["ExitCode"] == 0,
                "migration service completed successfully",
            )
            head = run("exec", "-T", "api", "alembic", "heads").split()[0]
            check(sql("SELECT version_num FROM alembic_version") == head, "schema at head")
            payload = {"list1": ["hello", "hello"], "list2": ["ß", "world"]}
            records = cli(payload, repeat=2)
            check(len(records) == 2 and records[0] == records[1], "CLI repeats reuse UUID")
            identifier = str(UUID(records[0]["id"]))
            expected = "HELLO, SS, HELLO, WORLD"
            check(records[0]["output"] == expected, "packaged CLI alternating output")
            check(get(host, f"/payloads/{identifier}") == {"output": expected}, "HTTP GET")
            check(
                sql(f"SELECT output FROM payloads WHERE id = '{identifier}'") == expected,
                "complete payload committed independently",
            )
            snapshot = cache_rows()
            check(len(json.loads(snapshot)) == 3, "three distinct cached transformations")
            shared = {"list1": ["world"], "list2": ["hello"]}
            check(cli(shared)[0]["output"] == "WORLD, HELLO", "overlapping payload output")
            run("down")

            # Mount only this probe; the application still comes from the built image.
            probe = temporary / "deployment_probe.py"
            probe.write_text(
                "from cache_service.main import create_app\n"
                "async def reject(source: str) -> str:\n"
                "    raise RuntimeError('Unexpected transformation after restart')\n"
                "def app():\n"
                "    return create_app(transformer=reject)\n",
                encoding="utf-8",
            )
            restart = temporary / "restart.yaml"
            restart.write_text(
                "services:\n  api:\n"
                f"    volumes: [{json.dumps(str(probe) + ':/probe/deployment_probe.py:ro')}]\n"
                "    command: [uvicorn, deployment_probe:app, --factory, --app-dir, /probe, "
                "--host, 0.0.0.0, --port, '8000']\n",
                encoding="utf-8",
            )
            compose.extend(["-f", str(restart)])
            run("up", "-d", timeout=180)
            host = address()
            ready(host)
            check(get(host, f"/payloads/{identifier}") == {"output": expected}, "UUID survives")
            check(cli(payload)[0] == records[0], "identical input reuses persisted UUID")
            reordered = {"list1": ["ß", "world"], "list2": ["hello", "hello"]}
            check(
                cli(reordered)[0]["output"] == "SS, HELLO, WORLD, HELLO",
                "new payload reuses cache with transformer disabled after recreation",
            )
            check(cache_rows() == snapshot, "persisted cache records unchanged")
            # Prove the rejecting probe is active rather than silently using production code.
            request = Request(
                f"{host}/payloads",
                data=json.dumps({"list1": ["uncached"], "list2": ["hello"]}).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urlopen(request, timeout=10):
                    raise RuntimeError("Restart probe did not reject uncached input")
            except HTTPError as error:
                check(error.code == 502, "uncached input rejected by restart probe")
            else:
                raise RuntimeError("Restart probe did not reject uncached input")
        finally:
            run("down")
            print(f"Containers stopped; retained volume: {project}_postgres-data", flush=True)


if __name__ == "__main__":
    main()
