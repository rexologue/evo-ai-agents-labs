"""CLI для запуска профильного агента вне MCP."""

from __future__ import annotations

import asyncio
import sys

from dotenv import find_dotenv, load_dotenv

from .profile_agent import run_profile_agent


def main() -> None:
    """Запускает агент, используя аргумент CLI как описание компании."""

    load_dotenv(find_dotenv())
    if len(sys.argv) < 2:
        print("Передайте описание компании одной строкой")
        sys.exit(1)
    description = sys.argv[1]
    result = asyncio.run(run_profile_agent(description))
    print(result)


if __name__ == "__main__":
    main()
