from __future__ import annotations

from scripts.check_lean_proof_trust import NATIVE_DECIDE, first_violation, main


def test_proof_trust_scanner_rejects_executable_shortcuts() -> None:
    cases = [
        "theorem bad : True := by sorry\n",
        "theorem bad : True := by admit\n",
        "axiom bad : True\n",
        "@[deprecated] axiom bad : True\n",
        "theorem bad : True := by\n  exact sorry\n",
        f"theorem bad : True := by {NATIVE_DECIDE}\n",
        "theorem bad : True := by decide +native\n",
        "theorem bad : True := by decide (config := { native := true })\n",
        "unsafe def bad : Nat := 1\n",
        "partial def bad : Nat -> Nat := fun n => bad n\n",
        "set_option maxHeartbeats 0\nexample : True := by trivial\n",
        "set_option maxRecDepth 0 in\nexample : True := by trivial\n",
    ]
    for source in cases:
        assert first_violation(source) is not None


def test_proof_trust_scanner_ignores_prose_and_accepts_kernel_proofs() -> None:
    assert first_violation(f"/- {NATIVE_DECIDE} -/\ntheorem ok : True := by trivial\n") is None
    assert first_violation(f'def label := "{NATIVE_DECIDE}"\n') is None
    assert first_violation("/- unsafe def bad : Nat := 1 -/\ndef safe : Nat := 1\n") is None
    assert first_violation("theorem axiom_name_is_harmless : True := by trivial\n") is None
    assert first_violation("theorem arithmetic : 2004 % 12 = 0 := by decide\n") is None


def test_shipped_lean_tree_meets_proof_trust_floor() -> None:
    assert main() == 0
