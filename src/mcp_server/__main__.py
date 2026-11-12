"""python -m src.mcp_server --role <orchestration|allocator|checker>  (stdio transport)."""

from __future__ import annotations

import argparse

from .server import ROLE_TOOLS, build


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True, choices=sorted(ROLE_TOOLS))
    build(ap.parse_args().role).run("stdio")


if __name__ == "__main__":
    main()
