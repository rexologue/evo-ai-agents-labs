from __future__ import annotations

import sys

from dotenv import load_dotenv, find_dotenv

from .profile_agent import run_profile_agent


def main():
    load_dotenv(find_dotenv())
    if len(sys.argv) < 2:
        print("Передайте описание компании одной строкой")
        sys.exit(1)
    description = sys.argv[1]
    result = run_profile_agent(description)
    print(result)


if __name__ == "__main__":
    main()
