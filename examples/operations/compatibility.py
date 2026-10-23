#!/usr/bin/env python3
"""Preserve a reviewed cancel operation in a finite document-editing model."""

import copy
import json

from plectis.compatibility import check_certificate, compare


def models():
    """These are explicit models, not models extracted from a real editor."""
    approved = {
        "name": "reviewed document interface",
        "initial": "clean",
        "inputs": ["begin", "append", "cancel", "read"],
        "states": {
            "clean": {"begin": {"next": "draft", "output": "ok"},
                      "read": {"next": "clean", "output": "base"}},
            "draft": {"append": {"next": "edited", "output": "ok"},
                      "cancel": {"next": "clean", "output": "ok"},
                      "read": {"next": "draft", "output": "base"}},
            "edited": {"cancel": {"next": "clean", "output": "ok"},
                       "read": {"next": "edited", "output": "base+edit"}},
        },
    }
    extension = copy.deepcopy(approved)
    extension["name"] = "candidate with an inspection operation"
    extension["inputs"].append("inspect")
    for state, transitions in extension["states"].items():
        transitions["inspect"] = {"next": state, "output": "available"}

    regression = copy.deepcopy(extension)
    regression["name"] = "candidate whose cancel leaks an edit"
    regression["states"]["edited"]["cancel"]["next"] = "leaked"
    regression["states"]["leaked"] = {
        "begin": {"next": "draft", "output": "ok"},
        "read": {"next": "leaked", "output": "base+edit"},
    }
    return approved, extension, regression


def main():
    approved, extension, regression = models()
    accepted = compare(approved, extension)
    assert accepted["accepted"]
    assert check_certificate(approved, extension, accepted["certificate"])
    rejected = compare(approved, regression)
    assert rejected["continuation"] == ["begin", "append", "cancel", "read"]
    print(json.dumps({"extension": accepted, "regression": rejected}, indent=2))


if __name__ == "__main__":
    main()
