namespace MicrocosmProofWitness

theorem nat_add_zero_public (n : Nat) : n + 0 = n := Nat.add_zero n

theorem bool_and_true_public (b : Bool) : (b && true) = b := by
  cases b <;> rfl

theorem and_comm_public (p q : Prop) : p ∧ q -> q ∧ p := by
  intro h
  exact And.intro h.right h.left

theorem eq_self_public (n : Nat) : n = n := rfl

theorem closed_nat_mod_public : 17 % 5 = 2 := by
  decide

theorem or_comm_public (p q : Prop) : p ∨ q -> q ∨ p := by
  intro h
  cases h with
  | inl hp => exact Or.inr hp
  | inr hq => exact Or.inl hq

theorem eq_symm_public (a b : Nat) : a = b -> b = a := by
  intro h
  exact h.symm

theorem list_append_nil_public (xs : List Nat) : xs ++ [] = xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      simp [List.append, ih]

end MicrocosmProofWitness
