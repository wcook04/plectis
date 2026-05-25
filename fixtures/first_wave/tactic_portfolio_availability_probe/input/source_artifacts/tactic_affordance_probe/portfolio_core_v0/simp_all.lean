import Std

theorem tactic_probe_simp_all (p : Prop) (h : p) : p := by
  simp_all
