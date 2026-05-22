namespace MicrocosmProofWitness

theorem nat_add_zero_public (n : Nat) : n + 0 = n := Nat.add_zero n

theorem bool_and_true_public (b : Bool) : (b && true) = b := by
  cases b <;> rfl

theorem and_comm_public (p q : Prop) : p ∧ q -> q ∧ p := by
  intro h
  exact And.intro h.right h.left

theorem eq_self_public (n : Nat) : n = n := rfl

#check nat_add_zero_public
#check bool_and_true_public
#check and_comm_public
#check eq_self_public

end MicrocosmProofWitness
