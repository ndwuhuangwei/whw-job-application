"""Read-only resume inventory and artifact freshness checks (standard library)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone

SKIP_DIRS = {"qa", "review", "review-industrial", "node_modules", "__pycache__"}


def fingerprint(path: Path) -> dict:
    path = path.expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size, after.st_mtime_ns, after.st_ino
    ):
        raise ValueError(f"File changed while reading: {path}")
    return {
        "path": path.as_posix(),
        "sha256": digest.hexdigest(),
        "size_bytes": after.st_size,
        "modified_at": datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat(),
    }


def excluded(name: str) -> bool:
    lowered = name.casefold()
    return name.startswith(".") or "stale" in lowered or lowered in SKIP_DIRS


def catalog(root: Path) -> dict:
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Catalog root must be a directory")
    versions = []
    errors = []
    def on_walk_error(error):
        errors.append({"path": str(error.filename), "error": str(error)})

    for current, directories, names in os.walk(root, followlinks=False, onerror=on_walk_error):
        folder = Path(current)
        directories[:] = [
            name for name in directories
            if not excluded(name) and not (folder / name).is_symlink()
            and not getattr(folder / name, "is_junction", lambda: False)()
        ]
        if folder.name.casefold() != "src":
            continue
        sources = sorted(folder.glob("*.tex"))
        if not sources:
            continue
        version = folder.parent
        try:
            entries = sorted(version.iterdir())
            row = {
                "version_dir": version.as_posix(),
                "sources": [fingerprint(path) for path in sources if not path.is_symlink()],
                "pdfs": [p.as_posix() for p in entries if p.is_file() and p.suffix.lower() == ".pdf"],
                "review_html": [p.as_posix() for p in entries if p.is_file() and p.suffix.lower() == ".html"],
                "records": [
                    p.as_posix() for p in entries
                    if p.is_file() and (
                        p.name.casefold() == "readme.md"
                        or (p.suffix.lower() == ".json" and any(
                            token in p.name.casefold() for token in ("ledger", "log", "verification", "state")
                        ))
                    )
                ],
                "confirmation_status": "requires_evidence",
            }
            if row["sources"]:
                versions.append(row)
        except (OSError, ValueError) as error:
            errors.append({"path": version.as_posix(), "error": str(error)})
    versions.sort(
        key=lambda row: max(source["modified_at"] for source in row["sources"]),
        reverse=True,
    )
    return {
        "root": root.as_posix(),
        "complete": not errors,
        "count": len(versions),
        "note": "Times are discovery hints, not confirmation or match rankings. Only src/*.tex versions are indexed.",
        "versions": versions,
        "errors": errors,
    }


def verify(state: dict) -> dict:
    if not isinstance(state, dict):
        raise ValueError("State must be an object")
    artifacts = state.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Nonempty artifacts array required; no recorded hashes means not verified")
    seen = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            raise ValueError("Each artifact must be an object")
        path = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(path, str) or not Path(path).is_absolute():
            raise ValueError("Each artifact requires an absolute path")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            raise ValueError("Each artifact requires a 64-character SHA-256")
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            raise ValueError(f"Duplicate artifact path: {path}")
        seen.add(key)
    results = []
    for entry in artifacts:
        result = {"role": entry.get("role"), "path": entry["path"]}
        try:
            actual = fingerprint(Path(entry["path"]))
            result["status"] = "unchanged" if actual["sha256"] == entry["sha256"].lower() else "changed"
            if result["status"] == "changed":
                result["expected_sha256"] = entry["sha256"].lower()
                result["actual_sha256"] = actual["sha256"]
        except FileNotFoundError:
            result["status"] = "missing"
        except (OSError, ValueError) as error:
            result.update(status="unreadable", error=str(error))
        results.append(result)
    return {
        "unchanged": all(item["status"] == "unchanged" for item in results),
        "artifacts": results,
        "note": "Byte freshness only; this does not establish approval, factual correctness, PDF quality, or website persistence.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("catalog", help="List src/*.tex resume versions without reading personal text")
    inventory.add_argument("--root", required=True, type=Path)
    hashes = commands.add_parser("fingerprint", help="Print SHA-256 records; writes no files")
    hashes.add_argument("paths", nargs="+", type=Path)
    check = commands.add_parser("verify", help="Check artifacts hashes recorded in an application state")
    check.add_argument("state", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = catalog(args.root)
            code = 0 if result["complete"] else 1
        elif args.command == "fingerprint":
            result = {"artifacts": [fingerprint(path) for path in args.paths]}
            code = 0
        else:
            result = verify(json.loads(args.state.read_text(encoding="utf-8-sig")))
            code = 0 if result["unchanged"] else 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
