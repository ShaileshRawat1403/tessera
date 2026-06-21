"""Helper script: extract commit metadata for a range."""

import subprocess
import sys


def extract(range_spec: str) -> list[dict[str, str]]:
    result = subprocess.run(
        ["git", "log", "--pretty=format:%h|%s|%an", "--no-merges", range_spec],
        capture_output=True,
        text=True,
        check=True,
    )
    out: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        sha, subject, author = line.split("|", 2)
        out.append({"sha": sha, "subject": subject, "author": author})
    return out


if __name__ == "__main__":
    for entry in extract(sys.argv[1] if len(sys.argv) > 1 else "HEAD~10..HEAD"):
        print(entry)
