"""Trusted JSON and injective rank adapter for the EvidenceDiff Dafny core."""


def _rows(value):
    if type(value) is not list:
        raise ValueError("evidence inputs must be lists")
    result = []
    for row in value:
        if type(row) is not dict:
            continue
        key = row.get("ledger_id")
        if not key:
            continue
        # JSON-safe scalar IDs retain Python's native hash, equality and sort
        # semantics; lists/dicts are unhashable in the source implementation.
        if type(key) not in (str, int, float, bool):
            raise ValueError("nonempty ledger_id must be a JSON scalar")
        result.append((key, row))
    return result


def evaluate(payload, kernel, _dafny):
    if type(payload) is not dict or set(payload) != {"lab", "oracle"}:
        raise ValueError("expected lab and oracle rows")
    lab = _rows(payload["lab"])
    oracle = _rows(payload["oracle"])
    # Python dictionaries preserve the first equal key object and last row,
    # including numeric equality such as True == 1. Assigned ranks are unique
    # per equality class and need not impose an ordering on unlike types.
    ranks = {}
    for key, _ in lab + oracle:
        if key not in ranks:
            ranks[key] = len(ranks)
    lab_ids = _dafny.Seq([ranks[key] for key, _ in lab])
    oracle_ids = _dafny.Seq([ranks[key] for key, _ in oracle])
    cells = kernel.default__.Compute(lab_ids, oracle_ids, len(ranks))

    # The core decides every category and last index. Python set objects below
    # select the same displayed representative as the original for equal but
    # differently typed numeric keys; they do not choose the output category.
    lab_set = set({key: row for key, row in lab})
    oracle_set = set({key: row for key, row in oracle})
    lab_repr = {ranks[key]: key for key in lab_set}
    oracle_repr = {ranks[key]: key for key in oracle_set}
    overlap_repr = {ranks[key]: key for key in oracle_set & lab_set}
    missed, extra, shared, missed_entries, extra_entries = [], [], [], [], []
    for rank, cell in enumerate(cells):
        if cell.category == 1:
            extra.append(lab_repr[rank])
            extra_entries.append(lab[cell.labLast][1])
        elif cell.category == 2:
            missed.append(oracle_repr[rank])
            missed_entries.append(oracle[cell.oracleLast][1])
        elif cell.category == 3:
            shared.append(overlap_repr[rank])
        else:
            raise ValueError("core returned absent or invalid key category")
    return {"missed_ledger_ids": sorted(missed), "extra_ledger_ids": sorted(extra),
            "overlap_ledger_ids": sorted(shared),
            "missed_entries": sorted(missed_entries, key=lambda row: row.get("ledger_id", "")),
            "extra_entries": sorted(extra_entries, key=lambda row: row.get("ledger_id", ""))}
