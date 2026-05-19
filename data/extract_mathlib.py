"""Extract (state_before, tactic, state_after) tuples from a Lean 4 repo via LeanDojo.

Modes
-----
--smoke  : extract from the toy Lake project at /var/leandojo-smoke. This is the
           Evening-1 confidence check — proves elan + Lean + LeanDojo + Python env
           are wired correctly without paying the cost of a Mathlib build.
default  : extract from Mathlib4 at the pinned commit recorded below.
           Not yet wired — Evening 2.

Pinned versions
---------------
Lean toolchain : leanprover/lean4:v4.29.1   (elan-managed at /var/elan)
LeanDojo       : 4.20.0                      (from pyproject.toml)
Mathlib4       : TBD — Evening 2. We will pin to a commit with a documented
                 LeanDojo prebuilt trace cache (FAIR public-files) so we don't
                 pay a multi-hour Mathlib build unattended. If no cache is
                 available, fall back to a local Mathlib build with notes in
                 data/EXTRACTION_LOG.md (gitignored).

Run
---
    uv run python data/extract_mathlib.py --smoke
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from lean_dojo import LeanGitRepo, trace

SMOKE_REPO_PATH = Path("/var/leandojo-smoke")
SMOKE_OUTPUT = Path("data/cache/SMOKE_OUTPUT.jsonl")


def smoke_commit() -> str:
    """Read HEAD of the local smoke Lake project."""
    if not (SMOKE_REPO_PATH / ".git").exists():
        raise FileNotFoundError(
            f"smoke fixture missing at {SMOKE_REPO_PATH}; "
            "re-run the Evening-1 setup that scaffolds it."
        )
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=SMOKE_REPO_PATH,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def state_str(state: Any) -> str:
    """Coerce LeanDojo TacticState / ProofFinished / ProofGivenUp to a readable string."""
    if state is None:
        return ""
    pp = getattr(state, "pp", None)
    if pp:
        return str(pp)
    return str(state)


def theorem_name(thm: Any) -> str:
    for attr in ("full_name", "name"):
        v = getattr(thm, attr, None)
        if v:
            return str(v)
    return repr(thm)


def _iter_attr(obj: Any, names: Iterable[str]) -> Iterable[Any]:
    """Try a list of attribute names (some are methods, some are properties) and return the first hit."""
    for name in names:
        v = getattr(obj, name, None)
        if v is None:
            continue
        return v() if callable(v) else v
    return []


def extract_tuples(repo_url: str, commit: str) -> list[dict[str, str]]:
    print(f"[extract] tracing {repo_url} @ {commit[:12]} ...", flush=True)
    repo = LeanGitRepo(repo_url, commit)
    traced_repo = trace(repo)

    tuples: list[dict[str, str]] = []
    for tf in _iter_attr(traced_repo, ("traced_files",)):
        theorems = _iter_attr(tf, ("get_traced_theorems", "traced_theorems"))
        file_path = getattr(getattr(tf, "lean_file", tf), "path", None)
        for tt in theorems:
            tactics = _iter_attr(tt, ("get_traced_tactics", "traced_tactics"))
            for tac in tactics:
                tuples.append(
                    {
                        "file": str(file_path) if file_path else "",
                        "theorem": theorem_name(getattr(tt, "theorem", tt)),
                        "state_before": state_str(getattr(tac, "state_before", None)),
                        "tactic": str(getattr(tac, "tactic", "")),
                        "state_after": state_str(getattr(tac, "state_after", None)),
                    }
                )
    return tuples


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="extract from /var/leandojo-smoke (Evening-1 confidence check)",
    )
    args = parser.parse_args()

    if not args.smoke:
        print(
            "ERROR: Mathlib extraction is not wired up yet (Evening 2). "
            "Use --smoke for the Evening-1 confidence check.",
            file=sys.stderr,
        )
        return 2

    commit = smoke_commit()
    # LeanDojo's url_to_repo strips no scheme — a file:// URL gets turned
    # into a literal `file:/...` directory. Pass the plain absolute path; it
    # falls through to the local-path branch (shutil.copytree into its cache).
    repo_url = str(SMOKE_REPO_PATH)
    tuples = extract_tuples(repo_url, commit)

    if len(tuples) < 3:
        print(
            f"ERROR: extracted only {len(tuples)} tuples; smoke target should yield >=3.",
            file=sys.stderr,
        )
        return 1

    SMOKE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with SMOKE_OUTPUT.open("w") as f:
        for t in tuples:
            f.write(json.dumps(t) + "\n")

    print(f"[extract] {len(tuples)} tuples extracted -> {SMOKE_OUTPUT}")
    print("[extract] first 3:")
    for t in tuples[:3]:
        print(json.dumps(t, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
