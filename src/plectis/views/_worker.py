"""Strict data decoder and caller of the actual Dafny-generated executable.

This is trusted/tested Python glue, not a sandbox or a verified JSON parser.
The worker receives public values only. Candidate text is never Python code.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import runpy
import sys

MAX_REQUEST = 2_000_000
MAX_DEPTH = 32
MAX_NODES = 4096
MAX_TEXT = 16384
MAX_ROWS = 2000
MAX_OUTPUT = 8_000_000
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}\Z")


class WireError(ValueError):
    pass


def exact(obj, keys):
    if type(obj) is not dict or set(obj) != set(keys):
        raise WireError("Unexpected or missing JSON keys")


def text_value(value):
    if type(value) is not str or len(value) > MAX_TEXT or any(0xD800 <= ord(x) <= 0xDFFF for x in value):
        raise WireError("Expected bounded Unicode scalar text")
    return _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, value))


def value(value):
    if type(value) is str:
        return R.Value_Text(text_value(value))
    if type(value) is bool:
        return R.Value_Flag(value)
    raise WireError("Only text and Boolean values are supported")


def decode_schema(schema):
    exact(schema, ("version", "fields"))
    if type(schema["version"]) is not int or schema["version"] != 1:
        raise WireError("Unsupported schema version")
    fields = schema["fields"]
    if type(fields) is not list or len(fields) > 128:
        raise WireError("Expected at most 128 schema fields")
    names, types, high = [], [], []
    for field in fields:
        exact(field, ("name", "type", "visibility"))
        name = field["name"]
        if type(name) is not str or not NAME.fullmatch(name) or name in names:
            raise WireError("Invalid or duplicate schema field name")
        if field["type"] not in ("text", "flag") or type(field["type"]) is not str:
            raise WireError("Unsupported field type")
        if field["visibility"] not in ("public", "private") or type(field["visibility"]) is not str:
            raise WireError("Unsupported visibility")
        names.append(name)
        types.append(R.Ty_TextTy() if field["type"] == "text" else R.Ty_FlagTy())
        high.append(field["visibility"] == "private")
    return names, _dafny.Seq(types), _dafny.Seq(high)


class Decoder:
    def __init__(self, names):
        self.names = names
        self.nodes = 0

    def step(self, node, depth):
        self.nodes += 1
        if depth > MAX_DEPTH or self.nodes > MAX_NODES:
            raise WireError("Plan exceeds depth or node limits")
        if type(node) is not dict or len(node) != 1:
            raise WireError("Each plan node must have exactly one constructor")
        return next(iter(node.items()))

    def expr(self, node, depth=0):
        tag, arg = self.step(node, depth)
        if tag == "literal":
            return R.Expr_Literal(value(arg))
        if tag == "input":
            if type(arg) is not str or arg not in self.names:
                raise WireError("Unknown input field")
            return R.Expr_Input(self.names.index(arg))
        if tag in ("concat", "equals"):
            if type(arg) is not list or len(arg) != 2:
                raise WireError("Binary expression requires two operands")
            constructor = R.Expr_Concat if tag == "concat" else R.Expr_Equals
            return constructor(self.expr(arg[0], depth + 1), self.expr(arg[1], depth + 1))
        raise WireError("Unsupported expression constructor")

    def cmd(self, node, depth=0):
        tag, arg = self.step(node, depth)
        if tag == "skip":
            if arg is not True:
                raise WireError("skip must be true")
            return R.Cmd_Skip()
        if tag == "emit":
            exact(arg, ("channel", "value"))
            if type(arg["channel"]) is not str or arg["channel"] not in ("public", "internal"):
                raise WireError("Unsupported output channel")
            return R.Cmd_Emit(arg["channel"] == "public", self.expr(arg["value"], depth + 1))
        if tag == "seq":
            if type(arg) is not list or len(arg) != 2:
                raise WireError("Sequence requires exactly two commands")
            return R.Cmd_Then(self.cmd(arg[0], depth + 1), self.cmd(arg[1], depth + 1))
        if tag == "if":
            exact(arg, ("condition", "then", "else"))
            return R.Cmd_Branch(self.expr(arg["condition"], depth + 1),
                                self.cmd(arg["then"], depth + 1), self.cmd(arg["else"], depth + 1))
        raise WireError("Unsupported command constructor")


def expr_json(expr, names):
    if expr.is_Literal:
        val = expr.value
        return {"literal": val.text.VerbatimString(False) if val.is_Text else val.flag}
    if expr.is_Input:
        return {"input": names[expr.slot]}
    tag = "concat" if expr.is_Concat else "equals"
    return {tag: [expr_json(expr.left, names), expr_json(expr.right, names)]}


def cmd_json(cmd, names):
    if cmd.is_Skip:
        return {"skip": True}
    if cmd.is_Emit:
        return {"emit": {"channel": "public" if cmd.public else "internal", "value": expr_json(cmd.value, names)}}
    if cmd.is_Then:
        return {"seq": [cmd_json(cmd.first, names), cmd_json(cmd.second, names)]}
    return {"if": {"condition": expr_json(cmd.condition, names),
                   "then": cmd_json(cmd.yes, names), "else": cmd_json(cmd.no, names)}}


def explain_rejection(cmd, types, high, pc=False, path="plan"):
    """Diagnostics are advisory. Only generated Checked decides acceptance."""
    if cmd.is_Skip:
        return None
    if cmd.is_Emit:
        if not R.default__.WellTypedExpr(cmd.value, types) or R.default__.ExprType(cmd.value, types) != R.Ty_TextTy():
            return path + ": emit expects a well-typed text expression"
        if cmd.public and pc:
            return path + ": public output occurrence depends on private control"
        if cmd.public and R.default__.Sensitive(cmd.value, high):
            return path + ": public output value depends on a private field"
        return None
    if cmd.is_Then:
        return explain_rejection(cmd.first, types, high, pc, path + ".seq[0]") or explain_rejection(cmd.second, types, high, pc, path + ".seq[1]")
    if not R.default__.WellTypedExpr(cmd.condition, types) or R.default__.ExprType(cmd.condition, types) != R.Ty_FlagTy():
        return path + ": condition expects a well-typed Boolean expression"
    next_pc = pc or R.default__.Sensitive(cmd.condition, high)
    return explain_rejection(cmd.yes, types, high, next_pc, path + ".then") or explain_rejection(cmd.no, types, high, next_pc, path + ".else")


def process(request):
    if type(request) is not dict or request.get("action") not in ("compile", "run"):
        raise WireError("Unsupported worker action")
    action = request["action"]
    exact(request, ("action", "schema", "plan") if action == "compile" else ("action", "schema", "plan", "rows"))
    names, types, high = decode_schema(request["schema"])
    plan = Decoder(names).cmd(request["plan"])
    accepted, sliced = R.default__.CheckAndSlice(types, high, plan)
    if not accepted:
        return {"ok": False, "kind": "rejected", "reason": explain_rejection(plan, types, high) or "Plan rejected"}
    public_fields = [name for i, name in enumerate(names) if not high[i]]
    read_indices = sorted(R.default__.CmdReads(sliced))
    if any(i < 0 or i >= len(high) or high[i] for i in read_indices):
        raise WireError("Generated core violated the declared read boundary")
    if action == "compile":
        return {"ok": True, "public_plan": cmd_json(sliced, names), "public_fields": public_fields,
                "read_fields": [names[i] for i in read_indices]}
    rows = request["rows"]
    if type(rows) is not list or len(rows) > MAX_ROWS:
        raise WireError("Expected at most 2000 public rows")
    traces, output_size = [], 0
    for row in rows:
        exact(row, public_fields)
        values = []
        for i, name in enumerate(names):
            if high[i]:
                # No private record value is requested, accessed or validated.
                values.append(value("" if types[i].is_TextTy else False))
            else:
                val = value(row[name])
                if R.default__.ValueType(val) != types[i]:
                    raise WireError("Public field has an incorrect type")
                values.append(val)
        accepted, trace = R.default__.CheckAndRun(types, high, _dafny.Seq(values), plan)
        if not accepted:
            raise WireError("Generated core refused the public environment")
        strings = [s.VerbatimString(False) for s in trace]
        output_size += sum(len(s.encode("utf-8")) for s in strings)
        if output_size > MAX_OUTPUT:
            raise WireError("Public output exceeds the documented size limit")
        traces.append(strings)
    return {"ok": True, "traces": traces}


def no_duplicates(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            raise WireError("Duplicate JSON key")
        result[key] = val
    return result


def process_main():
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
        if len(raw) > MAX_REQUEST:
            raise WireError("Input exceeds the documented JSON size limit")
        request = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates,
                             parse_constant=lambda _: (_ for _ in ()).throw(WireError("Non-finite JSON number")))
        response = process(request)
    except (WireError, ValueError, TypeError, KeyError, RecursionError, UnicodeError):
        # Do not reflect record values or arbitrary candidate text into errors.
        response = {"ok": False, "kind": "invalid", "reason": "Invalid or unsupported input; see the documented schema and limits"}
    print(json.dumps(response, ensure_ascii=True, separators=(",", ":"), allow_nan=False))


def main():
    global _dafny, R
    loader = runpy.run_path(str(Path(__file__).resolve().parents[1] / "_sealed_kernel.py"))
    with loader["sealed_kernel"](Path(__file__).with_name("_generated"), "Release"):
        import _dafny
        import Release as R
        process_main()


if __name__ == "__main__":
    main()
