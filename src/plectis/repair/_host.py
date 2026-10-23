"""Small single-writer repair host for declared, immutable JSON computations.

The graph planner/checker is generated from the proved Dafny program. This
adapter, its JSON/hashing/file operations, and user callbacks are NOT proved.
"""
from dataclasses import dataclass, field
import hashlib
import heapq
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Callable
import uuid

from ._worker import bad_constant, unique_object


AMBIGUOUS_STATUSES = frozenset({"requested", "unknown", "pending", "inflight"})


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":"))


def parse(text):
    return json.loads(text, object_pairs_hook=unique_object,
                      parse_constant=bad_constant)


def json_snapshot(value):
    """Reject implicit Python-to-JSON conversions and detach mutable aliases."""
    def visit(item):
        if item is None or type(item) in (str, int, bool, float):
            return
        if type(item) is list:
            for child in item:
                visit(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                visit(child)
            return
        raise ValueError("inputs and outputs must be JSON values with string keys")
    visit(value)
    return canonical(value)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(canonical(value) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class InvalidPlan(ValueError):
    pass


class StalePlan(InvalidPlan):
    pass


@dataclass(frozen=True, init=False)
class Task:
    id: str
    code_id: str
    version: str
    deps: tuple
    inputs_json: str
    contract: str
    environment: str
    freshness: str
    replayable: bool
    fn: Callable | None = field(compare=False, repr=False)

    def __init__(self, id, *, code_id, version, deps=(), inputs=None,
                 contract, environment, freshness, replayable=False, fn=None):
        for name, value in (("id", id), ("code_id", code_id), ("version", version),
                            ("contract", contract), ("environment", environment),
                            ("freshness", freshness)):
            if type(value) is not str or not value:
                raise ValueError(name + " must be an explicit nonempty string")
            object.__setattr__(self, name, value)
        if (type(deps) not in (tuple, list)
                or any(type(parent) is not str or not parent for parent in deps)
                or len(set(deps)) != len(deps)):
            raise ValueError("deps must be distinct task IDs, in semantic order")
        if type(replayable) is not bool:
            raise ValueError("replayable must be Boolean")
        if fn is not None and not callable(fn):
            raise ValueError("fn must be callable or None")
        if replayable and fn is None:
            raise ValueError("replayable tasks need a callback")
        object.__setattr__(self, "deps", tuple(deps))
        object.__setattr__(self, "inputs_json", json_snapshot(inputs))
        object.__setattr__(self, "replayable", replayable)
        object.__setattr__(self, "fn", fn)

    def descriptor(self):
        return {"id": self.id, "code_id": self.code_id, "version": self.version,
                "deps": list(self.deps), "inputs": parse(self.inputs_json),
                "contract": self.contract, "environment": self.environment,
                "freshness": self.freshness, "replayable": self.replayable}

    @property
    def descriptor_json(self):
        return canonical(self.descriptor())

    @property
    def signature(self):
        return digest(self.descriptor_json)


def topological(tasks):
    by_id = {}
    for task in tasks:
        if not isinstance(task, Task) or task.id in by_id:
            raise ValueError("expected Tasks with distinct IDs")
        by_id[task.id] = task
    children = {key: [] for key in by_id}
    remaining = {}
    for task in by_id.values():
        remaining[task.id] = len(task.deps)
        for parent in task.deps:
            if parent not in by_id:
                raise ValueError("unknown dependency: " + parent)
            children[parent].append(task.id)
    ready = [key for key in by_id if not remaining[key]]
    heapq.heapify(ready)
    order = []
    while ready:
        key = heapq.heappop(ready)
        order.append(key)
        for child in children[key]:
            remaining[child] -= 1
            if remaining[child] == 0:
                heapq.heappush(ready, child)
    if len(order) != len(by_id):
        raise ValueError("dependency cycle")
    return tuple(by_id[key] for key in order)


def kernel_request(request):
    """One isolated interpreter per call; there is deliberately no fallback."""
    worker = Path(__file__).resolve().with_name("_worker.py")
    try:
        request_text = canonical(request)
        completed = subprocess.run([sys.executable, "-I", "-B", str(worker)],
                                   input=request_text, text=True,
                                   capture_output=True, timeout=30, check=False)
    except (TypeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        raise InvalidPlan("kernel request failed") from error
    try:
        result = parse(completed.stdout)
    except (ValueError, TypeError) as error:
        raise InvalidPlan("kernel process returned invalid JSON") from error
    if type(result) is not dict:
        raise InvalidPlan("kernel process returned a non-object response")
    if completed.returncode or "error" in result:
        raise InvalidPlan(result.get("error", "kernel process failed"))
    return result


def make_plan(deps, roots, effects):
    """Return immutable ``(dirty, blocked)`` masks for a topological DAG.

    Each node's dependencies must be integer indices smaller than its index.
    Roots and effects must be Boolean vectors of the graph length. Malformed
    inputs raise :class:`InvalidPlan`. The generated producer's result always
    passes through the generated checker before returning.
    """
    result = kernel_request({"op": "make", "deps": deps,
                             "roots": roots, "effects": effects})
    if result.get("accepted") is not True:
        raise InvalidPlan("generated checker rejected generated plan")
    return tuple(result["dirty"]), tuple(result["blocked"])


def check_plan(deps, roots, effects, dirty, blocked):
    """Check proposed masks using the unchanged verified generated checker.

    Return False for a well-typed incorrect plan; raise :class:`InvalidPlan`
    for malformed inputs or checker failure. This checks supplied graph facts,
    not whether they describe the caller's actual workflow.
    """
    result = kernel_request({"op": "check", "deps": deps, "roots": roots,
                             "effects": effects, "dirty": dirty,
                             "blocked": blocked})
    accepted = result.get("accepted")
    if type(accepted) is not bool:
        raise InvalidPlan("kernel process returned an invalid verdict")
    return accepted


@dataclass(frozen=True)
class Plan:
    binding: str
    order: tuple
    deps: tuple
    roots: tuple
    effects: tuple
    dirty: tuple
    blocked: tuple
    reasons: tuple

    def classification(self):
        return {key: ("blocked" if self.blocked[i]
                      else "rerun" if self.dirty[i] else "reuse")
                for i, key in enumerate(self.order)}

    def request(self, op="check"):
        request = {"op": op, "deps": [list(parents) for parents in self.deps],
                   "roots": list(self.roots), "effects": list(self.effects)}
        if op == "check":
            request.update(dirty=list(self.dirty), blocked=list(self.blocked))
        return request


class EffectJournal:
    """Append-only API, retained independently of graph membership.

    A hash chain detects accidental editing; it is not an authenticated log or
    a defence against an adversary who can replace all local state.
    """
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else None
        self._events = []
        self.refresh()

    @property
    def events(self):
        return parse(canonical(self._events))

    def refresh(self):
        if self.path is not None:
            events = ([parse(line) for line in self.path.read_text("utf-8").splitlines()]
                      if self.path.exists() else [])
        else:
            events = self._events
        previous = ""
        attempts = {}
        for index, event in enumerate(events):
            if type(event) is not dict:
                raise ValueError("malformed effect journal")
            body = {key: value for key, value in event.items() if key != "hash"}
            if (event.get("seq") != index or event.get("previous") != previous
                    or event.get("hash") != digest(canonical(body))):
                raise ValueError("effect journal chain mismatch")
            attempt = event.get("attempt")
            if type(attempt) is not str or not attempt:
                raise ValueError("invalid effect attempt")
            kind = event.get("kind")
            if kind == "requested":
                if attempt in attempts or type(event.get("task")) is not str:
                    raise ValueError("invalid requested effect")
                attempts[attempt] = [event, event]
            elif kind in ("unknown", "confirmed"):
                if attempt not in attempts or attempts[attempt][1]["kind"] == "confirmed":
                    raise ValueError("invalid effect transition")
                attempts[attempt][1] = event
            else:
                raise ValueError("invalid effect status")
            previous = event["hash"]
        self._events = events
        return attempts

    def append(self, kind, attempt, **fields):
        self.refresh()
        body = dict(seq=len(self._events), previous=(self._events[-1]["hash"]
                    if self._events else ""), kind=kind, attempt=attempt, **fields)
        event = dict(body, hash=digest(canonical(body)))
        # Validate the proposed transition before any write.
        prior = self._events
        trial = EffectJournal()
        trial._events = prior + [event]
        trial.refresh()
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(canonical(event) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        self._events = prior + [event]

    def unresolved(self):
        return tuple({"attempt": attempt, "task": start["task"],
                      "status": latest["kind"]}
                     for attempt, (start, latest) in self.refresh().items()
                     if latest["kind"] != "confirmed")


@dataclass
class RunResult:
    reused: tuple
    executed: tuple
    blocked: tuple
    failed: dict
    outputs: dict
    unresolved_effects: tuple

    @property
    def settled(self):
        return not self.unresolved_effects and not self.blocked and not self.failed


class RepairSession:
    """One cooperative writer over declared computations and effect history.

    A persistent checkpoint defaults to the persistent companion journal
    ``str(checkpoint) + '.effects.jsonl'``. An explicit journal may select a
    different persistent path; a memory-only journal is rejected with a
    persistent checkpoint. These two files still have separate commit points.
    Sessions without a checkpoint may keep their journal entirely in memory.
    """

    def __init__(self, tasks, *, checkpoint=None, journal=None, records=None):
        self.tasks = topological(tasks)
        self.by_id = {task.id: task for task in self.tasks}
        self.checkpoint = Path(checkpoint) if checkpoint is not None else None
        if self.checkpoint is not None:
            if journal is None:
                journal = Path(str(self.checkpoint) + ".effects.jsonl")
            elif isinstance(journal, EffectJournal) and journal.path is None:
                raise ValueError("persistent checkpoint requires a persistent effect journal")
        self.journal = journal if isinstance(journal, EffectJournal) else EffectJournal(journal)
        if records is not None and checkpoint is not None:
            raise ValueError("use either initial records or a checkpoint file")
        if records is not None and type(records) is not dict:
            raise ValueError("records must be an object keyed by task ID")
        self._records = parse(json_snapshot(records or {}))
        self._refresh()

    @property
    def records(self):
        self._refresh()
        return parse(canonical(self._records))

    def _refresh(self):
        if self.checkpoint is not None:
            if self.checkpoint.exists():
                payload = parse(self.checkpoint.read_text("utf-8"))
                if (type(payload) is not dict or type(payload.get("format")) is not int
                        or payload["format"] != 1
                        or type(payload.get("records")) is not dict):
                    raise ValueError("malformed checkpoint container")
                self._records = payload["records"]
            else:
                self._records = {}
        self.journal.refresh()

    def _save(self):
        if self.checkpoint is not None:
            atomic_json(self.checkpoint, {"format": 1, "records": self._records})

    def _unresolved(self):
        unresolved = list(self.journal.unresolved())
        journal_tasks = {item["task"] for item in unresolved}
        # Conservatively retain ambiguous records imported from an older host,
        # even when its effect journal was not supplied and the task is pruned.
        for task_id, record in self._records.items():
            if (type(record) is dict and record.get("status") in AMBIGUOUS_STATUSES
                    and task_id not in journal_tasks):
                unresolved.append({"attempt": "checkpoint:" + task_id,
                                   "task": task_id, "status": record["status"]})
        return tuple(unresolved)

    @staticmethod
    def _prior_descriptor(record):
        try:
            text = record["descriptor_json"]
            descriptor = parse(text)
            if (type(text) is not str or canonical(descriptor) != text
                    or digest(text) != record["signature"]
                    or type(descriptor.get("replayable")) is not bool):
                return None
            return descriptor
        except (KeyError, TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _output(record):
        try:
            text = record["output_json"]
            if (record.get("status") != "complete" or type(text) is not str
                    or json_snapshot(parse(text)) != text
                    or digest(text) != record["output_digest"]):
                return None
            return text, record["output_digest"]
        except (KeyError, TypeError, ValueError, AttributeError):
            return None

    def _state(self):
        self._refresh()
        order = tuple(task.id for task in self.tasks)
        indices = {key: i for i, key in enumerate(order)}
        deps = tuple(tuple(indices[parent] for parent in task.deps) for task in self.tasks)
        attempts = self.journal.refresh()
        unresolved = {item["task"] for item in self._unresolved()}
        ever_effect = {start["task"] for start, _ in attempts.values()}
        roots, effects, reasons = [], [], []
        for task in self.tasks:
            record = self._records.get(task.id)
            prior = self._prior_descriptor(record) if type(record) is dict else None
            why = []
            if record is None:
                why.append("missing checkpoint")
            else:
                if prior is None or record.get("signature") != task.signature:
                    why.append("descriptor changed or invalid")
                if self._output(record) is None:
                    why.append("missing, incomplete or corrupt output")
                expected = []
                for parent in task.deps:
                    output = self._output(self._records.get(parent))
                    expected.append([parent, output[1] if output else None])
                if (type(record) is not dict
                        or record.get("dependency_digests") != expected):
                    why.append("dependency output identity changed or missing")
                if any(value is None for _, value in expected):
                    why.append("dependency output unavailable")
                if (type(record) is dict and "effect_attempt" in record
                        and (type(record["effect_attempt"]) is not str
                             or not record["effect_attempt"])):
                    why.append("invalid external effect attempt identity")
            if task.id in unresolved:
                why.append("unsettled external effect")
            # A changed declaration cannot erase old effect/ambiguous history.
            old_effect = record is not None and (prior is None or not prior["replayable"]
                         or (type(record) is dict and "effect_attempt" in record))
            effects.append(not task.replayable or old_effect or task.id in ever_effect
                           or task.id in unresolved)
            roots.append(bool(why))
            reasons.append(tuple(why))
        binding = digest(canonical({"tasks": [task.descriptor() for task in self.tasks],
                                    "records": self._records,
                                    "journal": self.journal.events}))
        return binding, order, deps, tuple(roots), tuple(effects), tuple(reasons)

    def plan(self):
        binding, order, deps, roots, effects, reasons = self._state()
        dirty, blocked = make_plan(deps, roots, effects)
        return Plan(binding, order, deps, roots, effects, dirty, blocked, reasons)

    def _check_current(self, plan):
        binding, order, deps, roots, effects, _ = self._state()
        if not isinstance(plan, Plan):
            raise InvalidPlan("expected a Plan")
        if (plan.binding, plan.order, plan.deps, plan.roots, plan.effects) != (
                binding, order, deps, roots, effects):
            raise StalePlan("plan no longer binds the current tasks, records and journal")
        if not check_plan(plan.deps, plan.roots, plan.effects,
                          plan.dirty, plan.blocked):
            raise InvalidPlan("generated checker rejected candidate plan")

    def run(self, plan):
        """Check once, then dispatch only replayable reruns in this snapshot.

        Single-writer, synchronous API: callers must not mutate the checkpoint,
        journal or callback code during this call. Callbacks receive JSON copies.
        """
        self._check_current(plan)
        reused, executed, blocked, failed, outputs = [], [], [], {}, {}
        for i, task in enumerate(self.tasks):
            if plan.blocked[i]:
                blocked.append(task.id)
                continue
            if any(parent not in outputs for parent in task.deps):
                failed[task.id] = "dependency unavailable in this execution"
                continue
            if not plan.dirty[i]:
                output = self._output(self._records.get(task.id))
                if output is None:
                    raise InvalidPlan("reused output disappeared")
                outputs[task.id] = parse(output[0])
                reused.append(task.id)
                continue
            if not task.replayable or plan.effects[i] or task.fn is None:
                raise InvalidPlan("dispatch attempted to cross an effect boundary")
            dependency_digests = [[parent, self._records[parent]["output_digest"]]
                                  for parent in task.deps]
            base = {"descriptor_json": task.descriptor_json, "signature": task.signature,
                    "dependency_digests": dependency_digests}
            try:
                result = task.fn(parse(task.inputs_json),
                                 tuple(parse(canonical(outputs[parent]))
                                       for parent in task.deps))
                text = json_snapshot(result)
                self._records[task.id] = dict(base, status="complete", output_json=text,
                                              output_digest=digest(text))
                outputs[task.id] = parse(text)
                executed.append(task.id)
            except Exception as error:
                failed[task.id] = type(error).__name__ + ": " + str(error)
                self._records[task.id] = dict(base, status="failed", error=failed[task.id])
            self._save()
        return RunResult(tuple(reused), tuple(executed), tuple(blocked), failed, outputs,
                         self._unresolved())

    def begin_effect(self, task_id):
        """Record intent before an EXTERNAL resolver acts; never call its effect.

        A confirmed matching identity forbids retry even if its checkpoint was
        never saved. The journal and checkpoint have separate commit points.
        """
        plan = self.plan()
        if task_id not in self.by_id:
            raise ValueError("unknown effect task")
        i = plan.order.index(task_id)
        task = self.by_id[task_id]
        if not plan.effects[i] or not plan.dirty[i]:
            raise ValueError("task does not need external resolution")
        if any(item["task"] == task_id for item in self._unresolved()):
            raise ValueError("an existing effect attempt is unsettled; do not retry")
        if any(plan.dirty[parent] or plan.blocked[parent] for parent in plan.deps[i]):
            raise ValueError("effect dependencies are not ready")
        dependency_digests = [[parent, self._records[parent]["output_digest"]]
                              for parent in task.deps]
        for start, latest in self.journal.refresh().values():
            if (latest["kind"] == "confirmed" and start["task"] == task_id
                    and start.get("signature") == task.signature
                    and start.get("dependency_digests") == dependency_digests):
                raise ValueError("this effect identity is already confirmed; "
                                 "recover its checkpoint, do not retry")
        attempt = uuid.uuid4().hex
        self.journal.append("requested", attempt, task=task_id,
                            descriptor_json=task.descriptor_json, signature=task.signature,
                            dependency_digests=dependency_digests)
        return attempt

    def mark_unknown(self, attempt, reason):
        if type(reason) is not str or not reason:
            raise ValueError("provide an explicit ambiguity reason")
        self.journal.append("unknown", attempt, reason=reason)

    def resolve_effect(self, attempt, output):
        """Import a result from a trusted resolver; this does not prove its claim.

        The checkpoint retains the descriptor/dependencies of the original
        attempt, so resolving an old attempt cannot validate changed inputs.
        """
        self._refresh()
        attempts = self.journal.refresh()
        if attempt not in attempts or attempts[attempt][1]["kind"] == "confirmed":
            raise ValueError("attempt must be requested or unknown")
        start, _ = attempts[attempt]
        text = json_snapshot(output)
        record = {key: start[key] for key in ("descriptor_json", "signature",
                                             "dependency_digests")}
        record.update(status="complete", output_json=text, output_digest=digest(text),
                      effect_attempt=attempt)
        self.journal.append("confirmed", attempt, output_json=text, output_digest=digest(text))
        self._records[start["task"]] = record
        self._save()
