from __future__ import annotations

import argparse

from microcosm_core.organs import pattern_binding_contract
from microcosm_core.validators import private_state_scan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="microcosm")
    subparsers = parser.add_subparsers(dest="command")
    scan_parser = subparsers.add_parser("private-state-scan")
    scan_parser.add_argument("--root", required=True)
    scan_parser.add_argument("--out", required=True)
    scan_parser.add_argument("--policy")

    organ_parser = subparsers.add_parser("pattern-binding")
    organ_parser.add_argument("action", choices=["validate"])
    organ_parser.add_argument("--input", required=True)
    organ_parser.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    if args.command == "private-state-scan":
        return private_state_scan.main(["--root", args.root, "--out", args.out] + (["--policy", args.policy] if args.policy else []))
    if args.command == "pattern-binding":
        return pattern_binding_contract.main([args.action, "--input", args.input, "--out", args.out])
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
