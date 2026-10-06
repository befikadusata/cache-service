"""Create local credentials without printing them or overwriting existing configuration."""

import argparse
import os
import secrets
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--database-port", type=int, default=5432)
args = parser.parse_args()
if not 1 <= args.database_port <= 65535:
    parser.error("database port must be between 1 and 65535")
password = secrets.token_hex(32)
path = Path(__file__).resolve().parents[1] / ".env"
try:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    parser.exit(1, ".env already exists; preserve it and update it deliberately.\n")
with os.fdopen(descriptor, "w") as output:
    output.write(
        "DB_HOST=127.0.0.1\n"
        "DB_USER=cache\n"
        "DB_NAME=cache\n"
        f"DB_PASS={password}\n"
        f"DB_PORT={args.database_port}\n"
    )
print("Created .env with restricted permissions. Credentials were not printed.")
