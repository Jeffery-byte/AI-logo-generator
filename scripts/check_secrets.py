"""Reject common credential patterns in tracked current files; never print values.

This is a limited pattern check, not proof that all secrets have been detected.
Historical findings must be handled by revocation at the provider.
"""
from pathlib import Path
import re
import subprocess
import sys

PATTERNS = {
    "OpenAI API key": rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}",
    "Google API key": rb"\bAIza[0-9A-Za-z_-]{35}",
    "GitHub token": rb"\bgh[pousr]_[A-Za-z0-9]{30,}",
    "private key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "AWS access key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
}


def main():
    paths = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    findings = []
    for raw_path in paths:
        if not raw_path:
            continue
        path = Path(raw_path.decode())
        if not path.is_file():
            continue
        data = path.read_bytes()
        for label, pattern in PATTERNS.items():
            if re.search(pattern, data):
                findings.append(f"{path}: {label} pattern found")
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("No configured credential patterns found in the tracked current files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
