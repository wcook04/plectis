"""
[PURPOSE]
- Teleology: Enforce the "Holographic Shadow" documentation standard via static analysis.
- Mechanism: AST parsing (ast) plus tag extraction to validate required docstring structure.

[INTERFACE]
- Inputs: Python source path (Path).
- Outputs: ComplianceResult (bool + errors).
- Exports: audit_python_compliance, analyze_python_module, analyze_json_node.

[FLOW]
- Read source text.
- Parse into AST.
- Extract module-level docstring tags.
- Walk AST for ClassDef and FunctionDef nodes.
- Validate checks against configured rule sets.
- Return structured ModuleAnalysis.

[DEPENDENCIES]
- standard_lib.ast: parse (structural code inspection)
- standard_lib.re: _TAG_LINE_RE (docstring tag parsing)

[CONSTRAINTS]
- Atomicity: Analysis is read-only and must not mutate source files or global process state beyond configuration.
- Determinism: Given identical source text and configuration, analysis output is deterministic.
- Robustness: Must handle syntax errors and missing docstrings gracefully.
- Must support dynamic configuration via `configure_from_standard`.
- Escalates-to: codex/standards/std_python.py; codex/standards/std_python_scope_index.json; system/core/analysis.py::configure_from_standard; system/core/analysis.py::ComplianceResult

"""
from __future__ import annotations
import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Set
from dataclasses import dataclass, field

# --- GOVERNANCE CONFIGURATION (Safe Mode Defaults) ---
# These are overridden by configure_from_standard() at runtime.
_CONFIG_MODULE_TAGS: Set[str] = {'PURPOSE', 'INTERFACE', 'FLOW', 'DEPENDENCIES', 'CONSTRAINTS'}
_CONFIG_CLASS_TAG: str = 'ROLE'
_CONFIG_FUNC_TAG: str = 'ACTION'
_CONFIG_CONTRACT_ATOMS: Set[str] = {
    'Teleology', 'Mechanism', 'Guarantee', 'Forbid', 'Fails',
    'Warns', 'Reads', 'Writes', 'Locks', 'Orders', 'Schema',
    'Couples', 'Non-goal',
}
_CONFIG_OPTIONAL_CONTRACT_ATOMS: Set[str] = {
    'When-needed', 'Escalates-to',
}

def configure_from_standard(std: Dict[str, Any]) -> None:
    """
    [ACTION]
    - Teleology: Hydrates the validator with rules from the Python Standard definition.
    - Mechanism: Updates global configuration sets based on the input dictionary.
    - Fails: None (Safe defaults used).
    - Guarantee: Global config variables (_CONFIG_*) are updated.
    """
    global _CONFIG_MODULE_TAGS, _CONFIG_CLASS_TAG, _CONFIG_FUNC_TAG
    global _CONFIG_CONTRACT_ATOMS, _CONFIG_OPTIONAL_CONTRACT_ATOMS
    
    # 1. Module Tags
    mod_rules = std.get('module', {})
    if 'required_tags' in mod_rules:
        raw_tags = mod_rules['required_tags']
        if isinstance(raw_tags, list):
            _CONFIG_MODULE_TAGS = set(raw_tags)

    # 2. Class Tag
    cls_rules = std.get('public_class', {})
    if 'required_tags' in cls_rules:
        tags = cls_rules['required_tags']
        if isinstance(tags, list) and tags:
            _CONFIG_CLASS_TAG = str(tags[0])

    # 3. Function Tag
    fn_rules = std.get('public_function', {})
    if 'required_tags' in fn_rules:
        tags = fn_rules['required_tags']
        if isinstance(tags, list) and tags:
            _CONFIG_FUNC_TAG = str(tags[0])
    contract_atoms = std.get('contract_atoms')
    if isinstance(contract_atoms, list):
        _CONFIG_CONTRACT_ATOMS = {str(item).strip() for item in contract_atoms if str(item).strip()}
    optional_contract_atoms = std.get('optional_contract_atoms')
    if isinstance(optional_contract_atoms, list):
        _CONFIG_OPTIONAL_CONTRACT_ATOMS = {
            str(item).strip() for item in optional_contract_atoms if str(item).strip()
        }

@dataclass
class FunctionInfo:
    """
    [ROLE]
    - Teleology: Data container for function metadata extracted from AST.
    - Mechanism: Captures name, visibility, and parsed docstring tags for auditing.
    - Ownership: Owned by ModuleAnalysis; produced by AST walk functions.
    - Mutability: Immutable-by-convention after construction (dataclass instance).
    - Concurrency: Safe to use as a value object; no shared state.
    
    """
    name: str
    qualified_name: str = ""
    signature: str = ""
    doc: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    contract_atoms: Dict[str, List[str]] = field(default_factory=dict)
    is_private: bool = False
    is_async: bool = False
    line_start: int = 0
    line_end: int = 0
    calls: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    call_summary: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ClassInfo:
    """
    [ROLE]
    - Teleology: Data container for class metadata extracted from AST.
    - Mechanism: Captures name, methods, and parsed docstring tags for auditing.
    - Ownership: Owned by ModuleAnalysis; produced by AST walk functions.
    - Mutability: Immutable-by-convention after construction (dataclass instance).
    - Concurrency: Safe to use as a value object; no shared state.
    
    """
    name: str
    bases: List[str]
    doc: str
    tags: Dict[str, str]
    contract_atoms: Dict[str, List[str]]
    methods: List[FunctionInfo]
    is_private: bool = False

@dataclass
class ModuleAnalysis:
    """
    [ROLE]
    - Teleology: Comprehensive report on a module's compliance status.
    - Mechanism: Aggregates module tags plus per-class and per-function audit findings.
    - Ownership: Owned by the caller of `analyze_python_module`.
    - Mutability: Mutable while being built; treated as immutable after return.
    - Concurrency: Safe to pass between threads after construction; no internal synchronization.
    
    """
    path: str
    doc: str
    tags: Dict[str, str]
    contract_atoms: Dict[str, List[str]]
    classes: List[ClassInfo]
    functions: List[FunctionInfo]
    errors: List[str] = field(default_factory=list)
    is_compliant: bool = True
    parse_error: Optional[str] = None
    # --- Structured Compliance Data ---
    missing_module_tags: List[str] = field(default_factory=list)
    classes_missing_role: List[str] = field(default_factory=list)
    functions_missing_action: List[str] = field(default_factory=list)
    # --- Holographic Quality Data ---
    functions_missing_teleology: List[str] = field(default_factory=list)

@dataclass
class ComplianceResult:
    """
    [ROLE]
    - Teleology: High-level binary result of an audit.
    - Mechanism: Boolean flag plus list of error strings.
    - Ownership: Owned by the caller; derived from ModuleAnalysis.
    - Mutability: Mutable while accumulating errors; treated as immutable after return.
    - Concurrency: Safe to pass between threads after construction.
    
    """
    is_compliant: bool
    errors: List[str]

_TAG_LINE_RE = re.compile(r'^\s*\[(?P<tag>[A-Z_]+)\]\s*(?P<rest>.*)$')
_CONTRACT_ATOM_LINE_RE = re.compile(r'^\s*(?:-\s*)?(?P<atom>[A-Za-z][A-Za-z0-9-]*):\s*(?P<value>.*)$')


def _has_teleology(action_body: str) -> bool:
    """Return True if the [ACTION] body starts with a Teleology: atom."""
    for line in action_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            stripped = stripped[1:].strip()
        if not stripped:
            continue
        return stripped.startswith("Teleology:")
    return False

def extract_docstring_tags(docstring: Optional[str]) -> Dict[str, str]:
    """
    [ACTION]
    - Teleology: Parses raw docstrings into a dictionary of tags.
    - Mechanism: Regex-based line scanning for [TAG] patterns.
    - Fails: None.
    - Guarantee: Returns a dict (empty if no tags found).
    """
    if not docstring:
        return {}
    blocks: Dict[str, str] = {}
    current_tag: Optional[str] = None
    body_lines: List[str] = []
    
    for line in docstring.splitlines():
        m = _TAG_LINE_RE.match(line)
        if m:
            if current_tag is not None:
                blocks[current_tag] = '\n'.join(body_lines).strip()
            current_tag = m.group('tag').strip()
            body_lines = []
            rest = m.group('rest').strip()
            if rest:
                body_lines.append(rest)
        elif current_tag is not None:
            body_lines.append(line)
            
    if current_tag is not None:
        blocks[current_tag] = '\n'.join(body_lines).strip()
    return blocks


def extract_contract_atoms(tags: Mapping[str, str]) -> Dict[str, List[str]]:
    """
    [ACTION]
    - Teleology: Parse configured contract atoms from tagged docstring bodies into a structured mapping.
    - Mechanism: Scan each tag body line-by-line, capture known `Atom: value` bullets, and append indented continuation lines to the current atom.
    - Fails: None. Unknown atoms and malformed lines are ignored.
    - Guarantee: Returns only atoms declared by the active std_python configuration.
    """
    allowed_atoms = _CONFIG_CONTRACT_ATOMS | _CONFIG_OPTIONAL_CONTRACT_ATOMS
    atoms: Dict[str, List[str]] = {}
    for body in tags.values():
        current_atom: Optional[str] = None
        for raw_line in str(body or '').splitlines():
            stripped = raw_line.strip()
            if not stripped:
                current_atom = None
                continue
            match = _CONTRACT_ATOM_LINE_RE.match(raw_line)
            if match:
                atom_name = str(match.group('atom') or '').strip()
                if atom_name in allowed_atoms:
                    value = str(match.group('value') or '').strip()
                    atoms.setdefault(atom_name, [])
                    if value:
                        atoms[atom_name].append(value)
                    current_atom = atom_name
                    continue
                current_atom = None
                continue
            if current_atom and atoms.get(current_atom):
                atoms[current_atom][-1] = f"{atoms[current_atom][-1]} {stripped}".strip()
    return atoms


def extract_routing_atoms_from_text(text: str) -> Dict[str, List[str]]:
    """
    [ACTION]
    - Teleology: Extract optional routing atoms (When-needed, Escalates-to,
      Navigation-group, Couples) from a raw docstring body even when no
      `[BRACKETED]` tag sections are present. Lets bare module docstrings
      whose only convention is `- When-needed: ...` lines still emit
      authored routing atoms into the scope-index file row.
    - Mechanism: Walk the raw text line-by-line; the optional-atom subset
      is recognized everywhere, not only inside tagged bodies.
    - Fails: None. Returns an empty dict on empty/None input.
    - Guarantee: Returns only the optional routing-atom subset of the
      active std_python configuration; primary atoms (Teleology,
      Mechanism, etc.) remain tag-scoped to preserve grammar discipline.
    - Schema: {'When-needed': [str], 'Escalates-to': [str], 'Navigation-group': [str], 'Couples': [str]}
    """
    if not text:
        return {}
    optional_routing = _CONFIG_OPTIONAL_CONTRACT_ATOMS | {'Couples'}
    atoms: Dict[str, List[str]] = {}
    current_atom: Optional[str] = None
    for raw_line in str(text).splitlines():
        stripped = raw_line.strip()
        if not stripped:
            current_atom = None
            continue
        match = _CONTRACT_ATOM_LINE_RE.match(raw_line)
        if match:
            atom_name = str(match.group('atom') or '').strip()
            if atom_name in optional_routing:
                value = str(match.group('value') or '').strip()
                atoms.setdefault(atom_name, [])
                if value:
                    atoms[atom_name].append(value)
                current_atom = atom_name
                continue
            current_atom = None
            continue
        if current_atom and atoms.get(current_atom):
            atoms[current_atom][-1] = f"{atoms[current_atom][-1]} {stripped}".strip()
    return atoms


def _annotation_to_text(node: Optional[ast.AST]) -> str:
    if node is None or not hasattr(ast, 'unparse'):
        return ''
    try:
        return ast.unparse(node)
    except Exception:
        return ''


def _format_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args: List[str] = []
    args.extend(arg.arg for arg in node.args.posonlyargs)
    if node.args.posonlyargs:
        args.append('/')
    args.extend(arg.arg for arg in node.args.args)
    if node.args.vararg:
        args.append(f'*{node.args.vararg.arg}')
    elif node.args.kwonlyargs:
        args.append('*')
    args.extend(arg.arg for arg in node.args.kwonlyargs)
    if node.args.kwarg:
        args.append(f'**{node.args.kwarg.arg}')

    signature = f"({', '.join(args)})"
    return_annotation = _annotation_to_text(node.returns)
    if return_annotation:
        signature = f"{signature} -> {return_annotation}"
    return signature


def _safe_unparse(node: ast.AST) -> str:
    if not hasattr(ast, 'unparse'):
        return ''
    try:
        return ast.unparse(node)
    except Exception:
        return ''


def _attribute_chain(node: ast.AST) -> Optional[List[str]]:
    parts: List[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        parts.reverse()
        return parts
    return None


class _FunctionBodyMetadataVisitor(ast.NodeVisitor):
    def __init__(self, *, scope: str) -> None:
        self.scope = scope
        self.calls: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """
        [ACTION]
        - Teleology: Prevent the visitor from descending into nested function bodies.
        - Guarantee: Nested function definitions are not traversed.
        - Fails: None.
        """
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """
        [ACTION]
        - Teleology: Prevent the visitor from descending into nested async function bodies.
        - Guarantee: Nested async function definitions are not traversed.
        - Fails: None.
        """
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """
        [ACTION]
        - Teleology: Prevent the visitor from descending into nested class bodies.
        - Guarantee: Nested class definitions are not traversed.
        - Fails: None.
        """
        return None

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """
        [ACTION]
        - Teleology: Prevent the visitor from descending into lambda bodies.
        - Guarantee: Lambda expressions are not traversed.
        - Fails: None.
        """
        return None

    def visit_Import(self, node: ast.Import) -> None:
        """
        [ACTION]
        - Teleology: Record a bare import statement encountered in the function body.
        - Guarantee: An import record with kind "import" is appended to self.imports.
        - Fails: None.
        """
        names = [alias.name for alias in node.names]
        alias_map = {
            alias.name: alias.asname
            for alias in node.names
            if isinstance(alias.asname, str) and alias.asname.strip()
        }
        self.imports.append(
            {
                'kind': 'import',
                'module': '',
                'names': names,
                'alias_map': alias_map,
                'level': 0,
                'lineno': getattr(node, 'lineno', None),
                'end_lineno': getattr(node, 'end_lineno', None),
                'col_offset': getattr(node, 'col_offset', None),
                'scope': self.scope,
            }
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """
        [ACTION]
        - Teleology: Record a from-import statement encountered in the function body.
        - Guarantee: An import record with kind "from" is appended to self.imports.
        - Fails: None.
        """
        names = [alias.name for alias in node.names]
        alias_map = {
            alias.name: alias.asname
            for alias in node.names
            if isinstance(alias.asname, str) and alias.asname.strip()
        }
        self.imports.append(
            {
                'kind': 'from',
                'module': str(node.module or ''),
                'names': names,
                'alias_map': alias_map,
                'level': int(node.level or 0),
                'lineno': getattr(node, 'lineno', None),
                'end_lineno': getattr(node, 'end_lineno', None),
                'col_offset': getattr(node, 'col_offset', None),
                'scope': self.scope,
            }
        )

    def visit_Call(self, node: ast.Call) -> None:
        """
        [ACTION]
        - Teleology: Record a function or method call encountered in the function body.
        - Guarantee: A call record with target, kind, argument counts, and location metadata is appended to self.calls.
        - Fails: None.
        """
        target = _safe_unparse(node.func)
        target_kind = type(node.func).__name__.lower()
        owner_chain: List[str] = []
        is_method_call = isinstance(node.func, ast.Attribute)
        is_dynamic = not isinstance(node.func, (ast.Name, ast.Attribute))

        if isinstance(node.func, ast.Name):
            target = node.func.id
            target_kind = 'name'
        elif isinstance(node.func, ast.Attribute):
            chain = _attribute_chain(node.func)
            if chain:
                target = '.'.join(chain)
                owner_chain = chain[:-1]
                target_kind = 'attribute'
            else:
                is_dynamic = True
                target_kind = 'attribute'

        starargs_count = sum(1 for arg in node.args if isinstance(arg, ast.Starred))
        starargs_count += sum(1 for keyword in node.keywords if keyword.arg is None)
        self.calls.append(
            {
                'target': target,
                'target_kind': target_kind,
                'lineno': getattr(node, 'lineno', None),
                'end_lineno': getattr(node, 'end_lineno', None),
                'col_offset': getattr(node, 'col_offset', None),
                'end_col_offset': getattr(node, 'end_col_offset', None),
                'args_count': len(node.args),
                'kwargs_count': len([keyword for keyword in node.keywords if keyword.arg is not None]),
                'starargs_count': starargs_count,
                'call_repr': _safe_unparse(node),
                'owner_chain': owner_chain,
                'keyword_names': [keyword.arg for keyword in node.keywords if keyword.arg is not None],
                'is_method_call': is_method_call,
                'is_dynamic': is_dynamic,
            }
        )
        self.generic_visit(node)


def _extract_function_callsite_metadata(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    scope: str,
) -> Dict[str, Any]:
    visitor = _FunctionBodyMetadataVisitor(scope=scope)
    for statement in node.body:
        visitor.visit(statement)
    unique_targets = sorted(
        {
            str(item.get('target') or '').strip()
            for item in visitor.calls
            if str(item.get('target') or '').strip()
        }
    )
    return {
        'calls': visitor.calls,
        'imports': visitor.imports,
        'call_summary': {
            'call_count': len(visitor.calls),
            'import_count': len(visitor.imports),
            'unique_targets': unique_targets,
            'method_call_count': sum(1 for item in visitor.calls if item.get('is_method_call')),
            'dynamic_call_count': sum(1 for item in visitor.calls if item.get('is_dynamic')),
        },
    }


def _parse_function_node(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    scope: Optional[str] = None,
) -> FunctionInfo:
    doc = ast.get_docstring(node) or ''
    metadata = _extract_function_callsite_metadata(node, scope=scope or node.name)
    tags = extract_docstring_tags(doc)

    return FunctionInfo(
        name=node.name,
        qualified_name=scope or node.name,
        signature=_format_function_signature(node),
        doc=doc,
        tags=tags,
        contract_atoms=extract_contract_atoms(tags),
        is_private=node.name.startswith('_'),
        is_async=isinstance(node, ast.AsyncFunctionDef),
        line_start=getattr(node, 'lineno', 0),
        line_end=getattr(node, 'end_lineno', 0),
        calls=metadata['calls'],
        imports=metadata['imports'],
        call_summary=metadata['call_summary'],
    )

def _parse_class_node(node: ast.ClassDef) -> ClassInfo:
    doc = ast.get_docstring(node) or ''
    tags = extract_docstring_tags(doc)
    bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, 'unparse') else ['...']
    methods = []
    
    for sub in node.body:
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_parse_function_node(sub, scope=f'{node.name}.{sub.name}'))
            
    return ClassInfo(
        name=node.name,
        bases=bases,
        doc=doc,
        tags=tags,
        contract_atoms=extract_contract_atoms(tags),
        methods=methods,
        is_private=node.name.startswith('_')
    )

def analyze_python_module(path: Path) -> ModuleAnalysis:
    """
    [ACTION]
    - Teleology: Performs deep AST analysis of a Python file for compliance.
    - Mechanism: Reads file, parses AST, and validates against configured rules.
    - Fails: Returns ModuleAnalysis with parse_error set on Exception.
    - Guarantee: Always returns a ModuleAnalysis object.
    """
    try:
        source = path.read_text(encoding='utf-8', errors='replace')
        tree = ast.parse(source)
    except Exception as e:
        return ModuleAnalysis(
            path=str(path),
            doc='',
            tags={},
            contract_atoms={},
            classes=[],
            functions=[],
            errors=[f'Parse Error: {e}'],
            is_compliant=False,
            parse_error=str(e)
        )

    mod_doc = ast.get_docstring(tree) or ''
    mod_tags = extract_docstring_tags(mod_doc)
    mod_contract_atoms = extract_contract_atoms(mod_tags)
    # Also scan the raw module docstring for routing atoms outside any
    # `[BRACKETED]` section. Provider-authored docstrings emitted by the
    # python_navigation_population lane can carry just `- When-needed:` /
    # `- Escalates-to:` / `- Navigation-group:` lines without a `[PURPOSE]`
    # wrapper; those are still authored routing atoms and must reach the
    # scope-index file row. Tagged-body atoms take precedence; the merge
    # only fills empty keys.
    bare_routing = extract_routing_atoms_from_text(mod_doc)
    for atom_name, values in bare_routing.items():
        if atom_name not in mod_contract_atoms or not mod_contract_atoms[atom_name]:
            mod_contract_atoms[atom_name] = list(values)
    errors = []
    
    # Structured Data Containers
    missing_mod_tags = []
    missing_cls_roles = []
    missing_fn_actions = []
    missing_fn_teleology = []

    # 1. Check Module Tags (Dynamic Configuration)
    missing = [t for t in _CONFIG_MODULE_TAGS if t not in mod_tags or not mod_tags[t].strip()]
    if missing:
        errors.append(f'Module missing tags: {missing}')
        missing_mod_tags.extend(missing)

    classes = []
    functions = []

    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            c = _parse_class_node(stmt)
            classes.append(c)
            # 2. Check Class Tags (Dynamic Configuration)
            if not c.is_private and (not c.tags.get(_CONFIG_CLASS_TAG, '').strip()):
                errors.append(f"Class '{c.name}' missing [{_CONFIG_CLASS_TAG}]")
                missing_cls_roles.append(c.name)
            
            # 3. Check Method Tags (Inside Class) - **FIXED BLIND SPOT**
            for m in c.methods:
                if m.is_private:
                    continue
                full_name = f"{c.name}.{m.name}"
                action_body = m.tags.get(_CONFIG_FUNC_TAG, '').strip()
                if not action_body:
                    errors.append(f"Method '{full_name}' missing [{_CONFIG_FUNC_TAG}]")
                    missing_fn_actions.append(full_name)
                elif not _has_teleology(action_body):
                    missing_fn_teleology.append(full_name)
        
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            f = _parse_function_node(stmt)
            functions.append(f)
            # 4. Check Top-Level Function Tags
            if not f.is_private:
                action_body = f.tags.get(_CONFIG_FUNC_TAG, '').strip()
                if not action_body:
                    errors.append(f"Func '{f.name}' missing [{_CONFIG_FUNC_TAG}]")
                    missing_fn_actions.append(f.name)
                elif not _has_teleology(action_body):
                    missing_fn_teleology.append(f.name)

    return ModuleAnalysis(
        path=str(path),
        doc=mod_doc,
        tags=mod_tags,
        contract_atoms=mod_contract_atoms,
        classes=classes,
        functions=functions,
        errors=errors,
        is_compliant=len(errors) == 0,
        missing_module_tags=missing_mod_tags,
        classes_missing_role=missing_cls_roles,
        functions_missing_action=missing_fn_actions,
        functions_missing_teleology=missing_fn_teleology
    )

def audit_python_compliance(path: Path) -> ComplianceResult:
    """
    [ACTION]
    - Teleology: Wrapper for analysis that returns a simplified result.
    - Mechanism: Calls analyze_python_module and wraps output.
    - Fails: None.
    - Guarantee: Returns ComplianceResult.
    """
    res = analyze_python_module(path)
    return ComplianceResult(res.is_compliant, res.errors)

def analyze_json_node(path: Path) -> Tuple[bool, List[str]]:
    """
    [ACTION]
    - Teleology: Validates a JSON node against the Governance constraints.
    - Mechanism: Parses JSON and delegates to `audit_config_purity`.
    - Couples: system.core.governance.audit_config_purity
    - Fails: Catches JSONDecodeError and returns False.
    - Guarantee: Returns (is_valid, error_list).
    """
    try:
        raw = path.read_text(encoding='utf-8')
        data = json.loads(raw)
    except Exception as e:
        return (False, [f'JSON Error: {e}'])
        
    if not isinstance(data, dict):
        return (True, [])
        
    # Skip patcher operations or non-node payloads
    if 'patch_id' in data and isinstance(data.get('operations'), list):
        return (True, [])

    payload = data
    if data.get('type') == 'config' and isinstance(data.get('data'), dict):
        payload = data['data']
        
    try:
        from system.core.governance import audit_config_purity
        issues = audit_config_purity(payload)
        if issues:
            errors = []
            for i in issues:
                # Handle both ValidationIssue objects and dicts (legacy safety)
                if hasattr(i, 'message'):
                    msg = i.message
                    det = i.details if hasattr(i, 'details') else {}
                    p = det.get('path', '') if isinstance(det, dict) else getattr(det, 'path', '')
                    errors.append(f"{msg} ({p})")
                elif isinstance(i, dict):
                    errors.append(f"{i.get('message')} ({i.get('details', {}).get('path', '')})")
                else:
                    errors.append(str(i))
            return (False, errors)
    except ImportError:
        pass
        
    return (True, [])


try:
    from codex.standards.std_python import PYTHON_STANDARD as _PYTHON_STANDARD
except Exception:
    _PYTHON_STANDARD = None  # type: ignore

if isinstance(_PYTHON_STANDARD, dict):
    configure_from_standard(_PYTHON_STANDARD)
