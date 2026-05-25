import Std

theorem tactic_probe_omega (x y : Int) (h0 : 2 * 3 = x - 9) (h1 : 2 * (-5) = y + 1) : x = 15 ∧ y = -11 := by
  omega
