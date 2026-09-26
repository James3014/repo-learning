#!/usr/bin/env python3
"""Install or check the canonical RepoLearn Skill in explicit filesystem roots."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repolearn.deployment import (  # noqa: E402
    CURRENT_CONTRACT,
    DeploymentStage,
    inspect_skill_directory,
    sync_skill_install,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync the canonical RepoLearn Skill into explicit filesystem skill roots."
    )
    parser.add_argument(
        "--source",
        default=str(REPO_ROOT / "skills" / "repo-learning"),
        help="Canonical RepoLearn Skill directory.",
    )
    parser.add_argument(
        "--root",
        action="append",
        required=True,
        help="Parent skill root; target becomes <root>/repo-learning. Repeat as needed.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift only; do not mutate install roots.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser()
    source_status = inspect_skill_directory(
        source,
        stage=DeploymentStage.SOURCE,
        expected=CURRENT_CONTRACT,
    )
    if not source_status.current:
        print(
            f"SOURCE_DRIFT {source} defect={source_status.defect.value}",
            file=sys.stderr,
        )
        return 2

    drift = False
    for raw_root in args.root:
        root = Path(raw_root).expanduser()
        status = sync_skill_install(
            source,
            root,
            check_only=args.check,
            expected=CURRENT_CONTRACT,
        )
        target = root / "repo-learning"
        if status.current:
            action = "CURRENT" if args.check else "SYNCED"
            print(
                f"{action} {target} revision={CURRENT_CONTRACT.revision} "
                f"sha256={CURRENT_CONTRACT.content_sha256}"
            )
        else:
            drift = True
            print(
                f"DRIFT {target} defect={status.defect.value} "
                f"expected_revision={CURRENT_CONTRACT.revision}",
                file=sys.stderr,
            )

    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
