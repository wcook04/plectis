import Std

example (p q : Prop) : p -> q -> p ∧ q := by
  intro hp
  trace_state
  intro hq
  exact ⟨hp, hq⟩
