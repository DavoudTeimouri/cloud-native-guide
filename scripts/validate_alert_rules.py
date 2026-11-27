#!/usr/bin/env python3
"""Validate Prometheus alert rule YAML files parse and have required keys."""
import glob
import sys
import yaml


def main() -> int:
    files = sorted(glob.glob("monitoring/rules/*.yml"))
    if not files:
        print("ERROR: no alert rule files found in monitoring/rules/")
        return 1
    for f in files:
        with open(f) as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict) or "groups" not in data:
            print(f"ERROR: {f} missing 'groups'")
            return 1
        for g in data["groups"]:
            if "name" not in g or "rules" not in g:
                print(f"ERROR: {f} group missing 'name'/'rules'")
                return 1
            for r in g["rules"]:
                if "alert" not in r or "expr" not in r:
                    print(f"ERROR: {f} rule missing 'alert'/'expr'")
                    return 1
    print(f"validated {len(files)} alert rule file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
