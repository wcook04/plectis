-- Generated direct-prime emitted certificate shard: b10_L6_A11.
import Erdos257PeriodNoncollapse.CertificateKernel

set_option linter.unusedTactic false
set_option linter.unreachableTactic false

namespace Erdos257PeriodNoncollapse

theorem concrete_generated_b10_F6_A11_factorization_support_cases
    {p : Nat}
    (hp : p ∈ (6 : Nat).factorization.support) :
    p = 2 ∨ p = 3 := by
  rw [Nat.support_factorization] at hp
  have hp_prime : Nat.Prime p := Nat.prime_of_mem_primeFactors hp
  have hp_dvd : p ∣ 6 := (Nat.mem_primeFactors.mp hp).2.1
  have hp_le : p ≤ 6 := Nat.le_of_dvd (by decide : 0 < 6) hp_dvd
  have hp_pos : 0 < p := hp_prime.pos
  interval_cases p
  · exact False.elim ((by decide : ¬ Nat.Prime 1) hp_prime)
  · exact Or.inl rfl
  · exact Or.inr rfl
  · exact False.elim ((by decide : ¬ Nat.Prime 4) hp_prime)
  · exact False.elim ((by decide : ¬ 5 ∣ 6) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 6) hp_prime)

theorem concrete_generated_b10_F6_A11_p2_prime_witness :
    PrimeComponentWitness 6 11 10 2 7 := by
  refine ⟨(by decide : Nat.Prime 7), ?_, ?_⟩
  · have hquot : primeComponentQuotient 10 6 2 = 1001 := by decide
    rw [hquot]
    decide
  · have hquot : primeComponentQuotient 10 6 2 = 1001 := by decide
    rw [hquot]
    have hfactor : (1001 : Nat).factorization 7 = 1 := by
      rw [show (1001 : Nat) = 7 * 143 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 7),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 7 ∣ 143),
      ]
    rw [hfactor]
    have hA_factor : (11 : Nat).factorization 7 = 0 :=
      Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 7 ∣ 11)
    rw [hA_factor]
    decide

theorem concrete_generated_b10_F6_A11_p2_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 6 11 10 2 := by
  exact Or.inr (Or.inr ⟨7, concrete_generated_b10_F6_A11_p2_prime_witness⟩)

theorem concrete_generated_b10_F6_A11_p3_prime_witness :
    PrimeComponentWitness 6 11 10 3 3 := by
  refine ⟨(by decide : Nat.Prime 3), ?_, ?_⟩
  · have hquot : primeComponentQuotient 10 6 3 = 10101 := by decide
    rw [hquot]
    decide
  · have hquot : primeComponentQuotient 10 6 3 = 10101 := by decide
    rw [hquot]
    have hfactor : (10101 : Nat).factorization 3 = 1 := by
      rw [show (10101 : Nat) = 3 * 3367 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 3),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 3 ∣ 3367),
      ]
    rw [hfactor]
    have hA_factor : (11 : Nat).factorization 3 = 0 :=
      Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 3 ∣ 11)
    rw [hA_factor]
    decide

theorem concrete_generated_b10_F6_A11_p3_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 6 11 10 3 := by
  exact Or.inr (Or.inr ⟨3, concrete_generated_b10_F6_A11_p3_prime_witness⟩)

def emittedCertificate_b10_L6_A11 :
    EmittedCertificateTable 6 11 10 where
  rows := ({2, 3} : Finset Nat)
  L_ne_zero := by decide
  covers_factor_support := by
    intro p hp
    rcases concrete_generated_b10_F6_A11_factorization_support_cases hp with rfl | rfl <;>
      simp
  row_sound := by
    intro p hp
    simp at hp
    rcases hp with hp_eq | hp_eq
    · subst p
      exact EmittedGeneratedRowCase.prime_witness
        concrete_generated_b10_F6_A11_p2_prime_witness
    · subst p
      exact EmittedGeneratedRowCase.prime_witness
        concrete_generated_b10_F6_A11_p3_prime_witness

theorem orderOf_b10_mod90909_eq_6_from_emittedCertificate_denNorm :
    orderOf (ZMod.unitOfCoprime 10
      (by decide : Nat.Coprime 10 90909)) = 6 := by
  let hcop : Nat.Coprime 10 90909 := by decide
  have h_ord_dvd_L : orderOf (ZMod.unitOfCoprime 10 hcop) ∣ 6 := by
    have hpow_unit : (ZMod.unitOfCoprime 10 hcop) ^ 6 = 1 := by
      apply Units.ext
      change (((ZMod.unitOfCoprime 10 hcop : (ZMod 90909)ˣ) : ZMod 90909) ^ 6) =
        (1 : ZMod 90909)
      rw [ZMod.coe_unitOfCoprime]
      decide
    exact (orderOf_dvd_iff_pow_eq_one).2 hpow_unit
  exact finite_period_noncollapse_from_emitted_certificate_table
    6 11 999999 90909 10 hcop
    (by decide)
    (by decide)
    h_ord_dvd_L
    (by decide)
    (by decide)
    (by decide)
    (Nat.one_le_pow (orderOf (ZMod.unitOfCoprime 10 hcop)) 10 (by decide))
    emittedCertificate_b10_L6_A11

end Erdos257PeriodNoncollapse
