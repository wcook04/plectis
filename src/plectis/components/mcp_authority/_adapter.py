"""Strict JSON bridge for the generated MCP authority decision."""

FIELDS = (
    "declared", "scope", "broad", "credential", "forbiddenKey",
    "untrustedInstruction", "live", "finalOnly", "effect", "approval",
    "ledger", "rollback", "bodySafe", "privateSafe", "fieldsPresent", "toolClass",
    "argumentHash", "sourceCapsule", "instructionSplit", "coldReplay",
)
STRINGS = frozenset({"scope", "effect", "approval", "ledger", "rollback", "toolClass",
                     "argumentHash", "sourceCapsule", "instructionSplit", "coldReplay"})


def evaluate(payload, kernel, dafny):
    if type(payload) is not dict or set(payload) != {"positive", "negative"}:
        raise ValueError("expected positive and negative call lists")
    if any(type(payload[key]) is not list for key in ("positive", "negative")):
        raise ValueError("expected call lists")

    def encode(row):
        if type(row) is not dict or set(row) != set(FIELDS):
            raise ValueError("invalid call observations")
        if any(type(row[key]) is not (str if key in STRINGS else bool) for key in FIELDS):
            raise ValueError("invalid call observation type")
        return kernel.Call_Call(*(
            dafny.Seq(row[key]) if key in STRINGS else row[key] for key in FIELDS
        ))

    positive = [encode(row) for row in payload["positive"]]
    negative = [encode(row) for row in payload["negative"]]
    rows = dafny.Seq(positive)
    faults = [list(kernel.default__.Faults(row).Elements) for row in positive + negative]
    if any(len(row) != 10 or any(type(flag) is not bool for flag in row) for row in faults):
        raise ValueError("invalid generated faults")
    writes, untrusted, accepted = kernel.default__.Batch(rows)
    result = {
        "positive_faults": faults[:len(positive)],
        "negative_faults": faults[len(positive):],
        "write_count": writes,
        "untrusted_count": untrusted,
        "accepted": accepted,
    }
    if (type(result["accepted"]) is not bool or
            any(type(result[key]) is not int for key in ("write_count", "untrusted_count"))):
        raise ValueError("invalid generated batch decision")
    return result
