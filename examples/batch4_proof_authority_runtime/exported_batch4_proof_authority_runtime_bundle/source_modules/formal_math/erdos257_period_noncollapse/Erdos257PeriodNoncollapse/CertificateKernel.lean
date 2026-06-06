import Mathlib.Algebra.Ring.GeomSum
import Mathlib.Data.Nat.Choose.Dvd
import Mathlib.Data.Nat.Factorization.Basic
import Mathlib.Data.Nat.Find
import Mathlib.Data.Nat.ModEq
import Mathlib.Data.ZMod.Basic
import Mathlib.NumberTheory.Multiplicity

set_option linter.unusedTactic false
set_option linter.unreachableTactic false

namespace Erdos257PeriodNoncollapse

theorem no_prime_drop_implies_eq
    (d L : Nat)
    (hLpos : 0 < L)
    (h_dvd : d ∣ L)
    (h_no_drop : ∀ p, Nat.Prime p → p ∣ L → ¬ d ∣ L / p) :
    d = L := by
  rcases h_dvd with ⟨k, rfl⟩
  by_cases hk : k = 1
  · simp [hk]
  have hk_pos : 0 < k := by
    by_contra hk_nonpos
    have hk_zero : k = 0 := Nat.eq_zero_of_not_pos hk_nonpos
    simp [hk_zero] at hLpos
  obtain ⟨p, hp_prime, hp_dvd_k⟩ := Nat.exists_prime_and_dvd hk
  have hp_dvd_L : p ∣ d * k := dvd_mul_of_dvd_right hp_dvd_k d
  have hdvd_drop : d ∣ d * k / p := by
    rcases hp_dvd_k with ⟨m, rfl⟩
    refine ⟨m, ?_⟩
    rw [mul_comm p m, ← mul_assoc]
    exact Nat.mul_div_left _ hp_prime.pos
  exfalso
  exact (h_no_drop p hp_prime hp_dvd_L) hdvd_drop

theorem valuation_deficit_blocks_dvd
    {q M A : Nat}
    (_hq : Nat.Prime q)
    (hM : M ≠ 0)
    (hA : A ≠ 0)
    (hdef : M.factorization q > A.factorization q) :
    ¬ M ∣ A := by
  intro hdiv
  have hle : M.factorization q ≤ A.factorization q :=
    (Nat.factorization_le_iff_dvd hM hA).2 hdiv q
  exact Nat.not_lt_of_ge hle hdef

theorem factorization_le_of_dvd_ne_zero
    {q a b : Nat}
    (hb : b ≠ 0)
    (hab : a ∣ b) :
    a.factorization q ≤ b.factorization q := by
  have ha : a ≠ 0 := by
    intro ha
    rcases hab with ⟨c, hc⟩
    apply hb
    rw [hc, ha, zero_mul]
  exact (Nat.factorization_le_iff_dvd ha hb).2 hab q

theorem valuation_witnesses_imply_no_prime_drop
    (d L A : Nat)
    (M q : Nat → Nat)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_dvd : d ∣ L)
    (h_collapse_if_drop :
      ∀ p, Nat.Prime p → p ∣ L → d ∣ L / p → M p ∣ A)
    (h_q_prime :
      ∀ p, Nat.Prime p → p ∣ L → Nat.Prime (q p))
    (h_M_ne_zero :
      ∀ p, Nat.Prime p → p ∣ L → M p ≠ 0)
    (h_deficit :
      ∀ p, Nat.Prime p → p ∣ L →
        (M p).factorization (q p) > A.factorization (q p)) :
    d = L := by
  apply no_prime_drop_implies_eq d L hLpos h_dvd
  intro p hp hpL hdrop
  have hblock : ¬ M p ∣ A :=
    valuation_deficit_blocks_dvd
      (h_q_prime p hp hpL)
      (h_M_ne_zero p hp hpL)
      hA
      (h_deficit p hp hpL)
  exact hblock (h_collapse_if_drop p hp hpL hdrop)

theorem collapse_divisor_core
    {A B C M Q g : Nat}
    (hQpos : 0 < Q)
    (hB_MC : B = M * C)
    (hB_gQ : B = g * Q)
    (hQ_dvd_C : Q ∣ C)
    (hg_dvd_A : g ∣ A) :
    M ∣ A := by
  rcases hQ_dvd_C with ⟨t, ht⟩
  have hMg : M * t = g := by
    have hB_MtQ : B = (M * t) * Q := by
      rw [hB_MC, ht]
      ac_rfl
    have hmul : (M * t) * Q = g * Q := by
      rw [← hB_MtQ, hB_gQ]
    exact Nat.eq_of_mul_eq_mul_right hQpos hmul
  rcases hg_dvd_A with ⟨u, hu⟩
  refine ⟨t * u, ?_⟩
  rw [hu, ← hMg]
  ac_rfl

theorem gcd_denominator_factor
    (A B : Nat) :
    B = Nat.gcd A B * (B / Nat.gcd A B) := by
  have hdiv : Nat.gcd A B ∣ B := Nat.gcd_dvd_right A B
  rw [mul_comm]
  exact (Nat.div_mul_cancel hdiv).symm

theorem collapse_divisor_from_gcd_denominator
    {A B C M Q : Nat}
    (hQ : Q = B / Nat.gcd A B)
    (hB_MC : B = M * C)
    (hQ_dvd_C : Q ∣ C)
    (hQpos : 0 < Q) :
    M ∣ A := by
  exact collapse_divisor_core
    (A := A)
    (B := B)
    (C := C)
    (M := M)
    (Q := Q)
    (g := Nat.gcd A B)
    hQpos
    hB_MC
    (by
      rw [hQ]
      exact gcd_denominator_factor A B)
    hQ_dvd_C
    (Nat.gcd_dvd_left A B)

theorem period_witness_dvd_component
    {b Q d e : Nat}
    (hQ_period : Q ∣ b ^ d - 1)
    (hd_e : d ∣ e) :
    Q ∣ b ^ e - 1 := by
  exact dvd_trans hQ_period (Nat.pow_sub_one_dvd_pow_sub_one b hd_e)

theorem collapse_divisor_from_period_witness
    {A B C M Q b d e : Nat}
    (hQ : Q = B / Nat.gcd A B)
    (hB_MC : B = M * C)
    (hC_eq : C = b ^ e - 1)
    (hQ_period : Q ∣ b ^ d - 1)
    (hd_e : d ∣ e)
    (hQpos : 0 < Q) :
    M ∣ A := by
  exact collapse_divisor_from_gcd_denominator
    (A := A)
    (B := B)
    (C := C)
    (M := M)
    (Q := Q)
    hQ
    hB_MC
    (by
      rw [hC_eq]
      exact period_witness_dvd_component hQ_period hd_e)
    hQpos

theorem period_witness_certificate_implies_no_prime_drop
    (d L A B Q b : Nat)
    (M C q : Nat → Nat)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_dvd : d ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hQ_period : Q ∣ b ^ d - 1)
    (h_component_factor :
      ∀ p, Nat.Prime p → p ∣ L → B = M p * C p)
    (h_component_eq :
      ∀ p, Nat.Prime p → p ∣ L → C p = b ^ (L / p) - 1)
    (h_q_prime :
      ∀ p, Nat.Prime p → p ∣ L → Nat.Prime (q p))
    (h_M_ne_zero :
      ∀ p, Nat.Prime p → p ∣ L → M p ≠ 0)
    (h_deficit :
      ∀ p, Nat.Prime p → p ∣ L →
        (M p).factorization (q p) > A.factorization (q p)) :
    d = L := by
  apply valuation_witnesses_imply_no_prime_drop d L A M q hLpos hA h_dvd
  · intro p hp hpL hdrop
    exact collapse_divisor_from_period_witness
      (A := A)
      (B := B)
      (C := C p)
      (M := M p)
      (Q := Q)
      (b := b)
      (d := d)
      (e := L / p)
      hQ
      (h_component_factor p hp hpL)
      (h_component_eq p hp hpL)
      hQ_period
      hdrop
      hQpos
  · exact h_q_prime
  · exact h_M_ne_zero
  · exact h_deficit

theorem modEq_one_supplies_period_witness
    {b Q d : Nat}
    (hpow : 1 ≤ b ^ d)
    (hmod : b ^ d ≡ 1 [MOD Q]) :
    Q ∣ b ^ d - 1 := by
  exact (Nat.modEq_iff_dvd' hpow).1 hmod.symm

theorem collapse_divisor_from_modEq_period
    {A B C M Q b d e : Nat}
    (hQ : Q = B / Nat.gcd A B)
    (hB_MC : B = M * C)
    (hC_eq : C = b ^ e - 1)
    (hpow : 1 ≤ b ^ d)
    (hmod : b ^ d ≡ 1 [MOD Q])
    (hd_e : d ∣ e)
    (hQpos : 0 < Q) :
    M ∣ A := by
  exact collapse_divisor_from_period_witness
    (A := A)
    (B := B)
    (C := C)
    (M := M)
    (Q := Q)
    (b := b)
    (d := d)
    (e := e)
    hQ
    hB_MC
    hC_eq
    (modEq_one_supplies_period_witness hpow hmod)
    hd_e
    hQpos

theorem modEq_certificate_implies_no_prime_drop
    (d L A B Q b : Nat)
    (M C q : Nat → Nat)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_dvd : d ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hpow : 1 ≤ b ^ d)
    (hmod : b ^ d ≡ 1 [MOD Q])
    (h_component_factor :
      ∀ p, Nat.Prime p → p ∣ L → B = M p * C p)
    (h_component_eq :
      ∀ p, Nat.Prime p → p ∣ L → C p = b ^ (L / p) - 1)
    (h_q_prime :
      ∀ p, Nat.Prime p → p ∣ L → Nat.Prime (q p))
    (h_M_ne_zero :
      ∀ p, Nat.Prime p → p ∣ L → M p ≠ 0)
    (h_deficit :
      ∀ p, Nat.Prime p → p ∣ L →
        (M p).factorization (q p) > A.factorization (q p)) :
    d = L := by
  exact period_witness_certificate_implies_no_prime_drop
    d L A B Q b M C q
    hLpos
    hA
    h_dvd
    hQpos
    hQ
    (modEq_one_supplies_period_witness hpow hmod)
    h_component_factor
    h_component_eq
    h_q_prime
    h_M_ne_zero
    h_deficit

theorem orderOf_dvd_supplies_modEq
    {b Q d : Nat}
    (hcop : Nat.Coprime b Q)
    (hord_dvd : orderOf (ZMod.unitOfCoprime b hcop) ∣ d) :
    b ^ d ≡ 1 [MOD Q] := by
  have hunit_pow :
      (ZMod.unitOfCoprime b hcop) ^ d = 1 := by
    exact (orderOf_dvd_iff_pow_eq_one).1 hord_dvd
  have hzmod : ((b ^ d : Nat) : ZMod Q) = ((1 : Nat) : ZMod Q) := by
    have hcoerced :=
      congrArg (fun u : (ZMod Q)ˣ => (u : ZMod Q)) hunit_pow
    simpa [ZMod.coe_unitOfCoprime] using hcoerced
  exact (ZMod.natCast_eq_natCast_iff (b ^ d) 1 Q).1 hzmod

theorem orderOf_dvd_iff_modEq_one
    {b q n : Nat}
    (hcop : Nat.Coprime b q) :
    orderOf (ZMod.unitOfCoprime b hcop) ∣ n ↔ b ^ n ≡ 1 [MOD q] := by
  constructor
  · exact orderOf_dvd_supplies_modEq hcop
  · intro hmod
    apply (orderOf_dvd_iff_pow_eq_one).2
    apply Units.ext
    have hzmod : ((b ^ n : Nat) : ZMod q) = ((1 : Nat) : ZMod q) :=
      (ZMod.natCast_eq_natCast_iff (b ^ n) 1 q).2 hmod
    simpa [ZMod.coe_unitOfCoprime] using hzmod

theorem orderOf_dvd_iff_q_dvd_pow_sub_one
    {b q n : Nat}
    (hcop : Nat.Coprime b q)
    (hpow : 1 ≤ b ^ n) :
    orderOf (ZMod.unitOfCoprime b hcop) ∣ n ↔ q ∣ b ^ n - 1 := by
  constructor
  · intro hord
    exact modEq_one_supplies_period_witness hpow
      ((orderOf_dvd_iff_modEq_one hcop).1 hord)
  · intro hdiv
    apply (orderOf_dvd_iff_modEq_one hcop).2
    exact ((Nat.modEq_iff_dvd' hpow).2 hdiv).symm

theorem odd_prime_order_padicVal_pow_sub_one
    {b q d k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0) :
    padicValNat q (b ^ (d * k) - 1) =
      padicValNat q (b ^ d - 1) + padicValNat q k := by
  letI : Fact (Nat.Prime q) := ⟨hq⟩
  have hbase_dvd : q ∣ b ^ d - 1 := by
    have hord : orderOf (ZMod.unitOfCoprime b hcop) ∣ d := by
      rw [hd_order]
    exact (orderOf_dvd_iff_q_dvd_pow_sub_one hcop (le_of_lt hbase_gt_one)).1 hord
  have hnot_dvd_base : ¬ q ∣ b ^ d := by
    have hcop_pow : Nat.Coprime (b ^ d) q := hcop.pow_left d
    exact (hq.coprime_iff_not_dvd).1 hcop_pow.symm
  simpa [pow_mul] using
    (padicValNat.pow_sub_pow
      (p := q)
      (x := b ^ d)
      (y := 1)
      hq_odd
      hbase_gt_one
      hbase_dvd
      hnot_dvd_base
      hk_ne_zero)

theorem factorization_left_factor_of_mul_eq
    {N Q D q : Nat}
    (hQ_ne_zero : Q ≠ 0)
    (hD_ne_zero : D ≠ 0)
    (hN : N = Q * D) :
    Q.factorization q = N.factorization q - D.factorization q := by
  rw [hN, Nat.factorization_mul hQ_ne_zero hD_ne_zero]
  simp

theorem odd_prime_order_factorization_pow_sub_one
    {b q d k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0) :
    (b ^ (d * k) - 1).factorization q =
      (b ^ d - 1).factorization q + k.factorization q := by
  rw [Nat.factorization_def (b ^ (d * k) - 1) hq]
  rw [Nat.factorization_def (b ^ d - 1) hq]
  rw [Nat.factorization_def k hq]
  exact odd_prime_order_padicVal_pow_sub_one
    hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero

theorem collapse_divisor_from_orderOf_drop
    {A B C M Q b d e : Nat}
    (hcop : Nat.Coprime b Q)
    (hord_dvd : orderOf (ZMod.unitOfCoprime b hcop) ∣ d)
    (hQ : Q = B / Nat.gcd A B)
    (hB_MC : B = M * C)
    (hC_eq : C = b ^ e - 1)
    (hd_e : d ∣ e)
    (hQpos : 0 < Q)
    (hpow : 1 ≤ b ^ d) :
    M ∣ A := by
  exact collapse_divisor_from_modEq_period
    hQ
    hB_MC
    hC_eq
    hpow
    (orderOf_dvd_supplies_modEq hcop hord_dvd)
    hd_e
    hQpos

theorem pow_sub_one_component_factor
    (b L e : Nat)
    (heL : e ∣ L) :
    b ^ L - 1 = ((b ^ L - 1) / (b ^ e - 1)) * (b ^ e - 1) := by
  have hdiv : b ^ e - 1 ∣ b ^ L - 1 :=
    Nat.pow_sub_one_dvd_pow_sub_one b heL
  exact (Nat.div_mul_cancel hdiv).symm

theorem pow_sub_one_component_factorization
    {b L e q : Nat}
    (heL : e ∣ L)
    (hquot_ne_zero : ((b ^ L - 1) / (b ^ e - 1)) ≠ 0)
    (hden_ne_zero : b ^ e - 1 ≠ 0) :
    (((b ^ L - 1) / (b ^ e - 1)).factorization q)
      =
    (b ^ L - 1).factorization q - (b ^ e - 1).factorization q := by
  exact factorization_left_factor_of_mul_eq
    (N := b ^ L - 1)
    (Q := (b ^ L - 1) / (b ^ e - 1))
    (D := b ^ e - 1)
    hquot_ne_zero
    hden_ne_zero
    (pow_sub_one_component_factor b L e heL)

theorem odd_prime_order_component_term_valuation
    {b q d K k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : k ∣ K)
    (hquot_ne_zero :
      ((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) ≠ 0)
    (hden_ne_zero : b ^ (d * k) - 1 ≠ 0) :
    (((b ^ (d * K) - 1) / (b ^ (d * k) - 1)).factorization q)
      =
    K.factorization q - k.factorization q := by
  have heL : d * k ∣ d * K := mul_dvd_mul_left d hkK
  have hquot :
      (((b ^ (d * K) - 1) / (b ^ (d * k) - 1)).factorization q)
        =
      (b ^ (d * K) - 1).factorization q -
        (b ^ (d * k) - 1).factorization q :=
    pow_sub_one_component_factorization
      (b := b)
      (L := d * K)
      (e := d * k)
      (q := q)
      heL
      hquot_ne_zero
      hden_ne_zero
  have hnum :
      (b ^ (d * K) - 1).factorization q =
        (b ^ d - 1).factorization q + K.factorization q :=
    odd_prime_order_factorization_pow_sub_one
      hq hq_odd hcop hd_order hbase_gt_one hK_ne_zero
  have hden :
      (b ^ (d * k) - 1).factorization q =
        (b ^ d - 1).factorization q + k.factorization q :=
    odd_prime_order_factorization_pow_sub_one
      hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero
  rw [hquot, hnum, hden]
  exact Nat.add_sub_add_left
    ((b ^ d - 1).factorization q)
    (K.factorization q)
    (k.factorization q)

theorem normalized_factorization_unit_not_dvd
    {q N : Nat}
    (hq : Nat.Prime q)
    (hN_ne_zero : N ≠ 0) :
    ¬ q ∣ N / q ^ (N.factorization q) := by
  have hpow_dvd_N : q ^ (N.factorization q) ∣ N := by
    exact (hq.pow_dvd_iff_le_factorization hN_ne_zero).2 le_rfl
  have hpow_pos : 0 < q ^ (N.factorization q) := pow_pos hq.pos _
  have hquot_pos : 0 < N / q ^ (N.factorization q) := by
    exact Nat.div_pos
      (Nat.le_of_dvd (Nat.pos_of_ne_zero hN_ne_zero) hpow_dvd_N)
      hpow_pos
  have hquot_ne_zero :
      N / q ^ (N.factorization q) ≠ 0 :=
    Nat.pos_iff_ne_zero.mp hquot_pos
  intro hdiv
  have hpos : 0 < (N / q ^ (N.factorization q)).factorization q :=
    hq.factorization_pos_of_dvd hquot_ne_zero hdiv
  have hzero :
      (N / q ^ (N.factorization q)).factorization q = 0 := by
    have hf :=
      congrArg (fun f : Nat →₀ Nat => f q)
        (Nat.factorization_div hpow_dvd_N)
    simpa [Nat.factorization_pow, Nat.Prime.factorization_self hq] using hf
  exact (Nat.not_lt_zero _) (hzero ▸ hpos)

theorem odd_prime_order_normalized_pow_sub_one_not_dvd
    {b q d k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0) :
    ¬ q ∣
      (b ^ (d * k) - 1) /
        q ^ ((b ^ d - 1).factorization q + k.factorization q) := by
  have hpow_gt_one : 1 < b ^ (d * k) := by
    rw [pow_mul]
    exact Nat.one_lt_pow hk_ne_zero hbase_gt_one
  have hN_ne_zero : b ^ (d * k) - 1 ≠ 0 :=
    Nat.sub_ne_zero_of_lt hpow_gt_one
  have hunit := normalized_factorization_unit_not_dvd
    (q := q)
    (N := b ^ (d * k) - 1)
    hq
    hN_ne_zero
  have hval := odd_prime_order_factorization_pow_sub_one
    (b := b)
    (q := q)
    (d := d)
    (k := k)
    hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero
  rwa [hval] at hunit

theorem odd_prime_order_component_term_normalized_not_dvd
    {b q d K k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : k ∣ K)
    (hquot_ne_zero :
      ((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) ≠ 0)
    (hden_ne_zero : b ^ (d * k) - 1 ≠ 0) :
    ¬ q ∣
      ((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) /
        q ^ (K.factorization q - k.factorization q) := by
  have hunit := normalized_factorization_unit_not_dvd
    (q := q)
    (N := (b ^ (d * K) - 1) / (b ^ (d * k) - 1))
    hq
    hquot_ne_zero
  have hval := odd_prime_order_component_term_valuation
    (b := b)
    (q := q)
    (d := d)
    (K := K)
    (k := k)
    hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero hK_ne_zero
    hkK hquot_ne_zero hden_ne_zero
  rwa [hval] at hunit

theorem exact_pow_div_eq_add_mul_of_eq_mul_add_pow_succ
    {q m N R C : Nat}
    (hqpos : 0 < q)
    (h :
      N = q ^ m * R + q ^ (m + 1) * C) :
    N / q ^ m = R + q * C := by
  rw [h]
  have hqm_pos : 0 < q ^ m := pow_pos hqpos _
  rw [pow_succ]
  rw [Nat.mul_assoc]
  rw [← Nat.mul_add]
  exact Nat.mul_div_cancel_left (R + q * C) hqm_pos

theorem exact_pow_div_modEq_of_eq_mul_add_pow_succ
    {q m N R C : Nat}
    (hqpos : 0 < q)
    (h :
      N = q ^ m * R + q ^ (m + 1) * C) :
    N / q ^ m ≡ R [MOD q] := by
  rw [exact_pow_div_eq_add_mul_of_eq_mul_add_pow_succ hqpos h]
  have hzero : q * C ≡ 0 [MOD q] := (Nat.modEq_zero_iff_dvd).2 ⟨C, rfl⟩
  exact Nat.ModEq.add_left R hzero

theorem exists_pow_first_order_any_exponent
    {q r u v : Nat}
    (_hqpos : 0 < q)
    (hr_pos : 0 < r) :
    ∃ C,
      (1 + q ^ r * u) ^ v =
        1 + q ^ r * (u * v) + q ^ (r + 1) * C := by
  cases r with
  | zero =>
      cases hr_pos
  | succ s =>
      induction v with
      | zero =>
          refine ⟨0, ?_⟩
          simp
      | succ v ih =>
          rcases ih with ⟨C, hC⟩
          refine ⟨C * (1 + q ^ (s + 1) * u) + q ^ s * ((u * v) * u), ?_⟩
          rw [pow_succ]
          rw [hC]
          ring_nf

theorem exists_pow_prime_step_first_order
    {q r u : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hr_pos : 0 < r) :
    ∃ C,
      (1 + q ^ r * u) ^ q =
        1 + q ^ (r + 1) * u + q ^ (r + 2) * C := by
  let f : Nat → Nat := fun m => (1 : Nat) ^ m * (q ^ r * u) ^ (q - m) * (q.choose m)
  have hq_ge3 : 3 ≤ q := by
    have hq_ne_two : q ≠ 2 := by
      intro h
      subst q
      rcases hq_odd with ⟨k, hk⟩
      omega
    have htwo : 2 ≤ q := hq.two_le
    omega
  have hq_two : 2 ≤ q := hq.two_le
  have hsplit : (∑ m ∈ Finset.range (q + 1), f m) =
      (∑ m ∈ Finset.range (q - 1), f m) + f (q - 1) + f q := by
    have hq_eq : q = (q - 1) + 1 := by omega
    calc
      (∑ m ∈ Finset.range (q + 1), f m)
          = (∑ m ∈ Finset.range q, f m) + f q := by
              simpa [Nat.add_comm] using (Finset.sum_range_succ f q)
      _ = ((∑ m ∈ Finset.range (q - 1), f m) + f (q - 1)) + f q := by
              conv_lhs => rw [hq_eq]
              rw [Finset.sum_range_succ]
              rw [← hq_eq]
      _ = (∑ m ∈ Finset.range (q - 1), f m) + f (q - 1) + f q := by
              ac_rfl
  have hhigh : q ^ (r + 2) ∣ (∑ m ∈ Finset.range (q - 1), f m) := by
    apply Finset.dvd_sum
    intro m hm
    have hm_lt_q_sub : m < q - 1 := Finset.mem_range.mp hm
    by_cases hm0 : m = 0
    · subst m
      have hle_exp : r + 2 ≤ r * q := by nlinarith
      have hpowdvd : q ^ (r + 2) ∣ q ^ (r * q) := Nat.pow_dvd_pow q hle_exp
      dsimp [f]
      simp [Nat.choose_zero_right]
      rw [mul_pow, ← pow_mul]
      exact dvd_mul_of_dvd_left hpowdvd (u ^ q)
    · have hm_lt_q : m < q := by omega
      have hq_choose : q ∣ q.choose m := hq.dvd_choose_self hm0 hm_lt_q
      have hqm_ge_two : 2 ≤ q - m := by omega
      have hle_exp : r + 1 ≤ r * (q - m) := by nlinarith
      have hpowdvd : q ^ (r + 1) ∣ (q ^ r * u) ^ (q - m) := by
        rw [mul_pow, ← pow_mul]
        exact dvd_mul_of_dvd_left (Nat.pow_dvd_pow q hle_exp) (u ^ (q - m))
      rcases hpowdvd with ⟨A, hA⟩
      rcases hq_choose with ⟨B, hB⟩
      refine ⟨A * B, ?_⟩
      dsimp [f]
      rw [hA, hB]
      rw [show r + 2 = (r + 1) + 1 by omega, pow_succ]
      ring_nf
  rcases hhigh with ⟨C, hC⟩
  refine ⟨C, ?_⟩
  rw [add_pow]
  change (∑ m ∈ Finset.range (q + 1), f m) = 1 + q ^ (r + 1) * u + q ^ (r + 2) * C
  rw [hsplit, hC]
  have hfq : f q = 1 := by
    dsimp [f]
    simp [Nat.choose_self]
  have hfqm1 : f (q - 1) = q ^ (r + 1) * u := by
    dsimp [f]
    have hsub : q - (q - 1) = 1 := by omega
    have hchoose : q.choose (q - 1) = q := by
      rw [Nat.choose_symm (show 1 ≤ q by omega)]
      simp [Nat.choose_one_right]
    rw [hsub, hchoose]
    ring_nf
  rw [hfq, hfqm1]
  ring

theorem exists_pow_q_iter_first_order
    {q a s u : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (ha_pos : 0 < a) :
    ∃ C,
      (1 + q ^ a * u) ^ (q ^ s) =
        1 + q ^ (a + s) * u + q ^ (a + s + 1) * C := by
  induction s with
  | zero =>
      refine ⟨0, ?_⟩
      simp
  | succ s ih =>
      rcases ih with ⟨C, hC⟩
      have has_pos : 0 < a + s := by omega
      obtain ⟨D, hD⟩ := exists_pow_prime_step_first_order
        (q := q) (r := a + s) (u := u + q * C) hq hq_odd has_pos
      refine ⟨C + D, ?_⟩
      rw [pow_succ]
      rw [pow_mul]
      rw [hC]
      have hbase :
          1 + q ^ (a + s) * u + q ^ (a + s + 1) * C =
            1 + q ^ (a + s) * (u + q * C) := by
        rw [show a + s + 1 = (a + s) + 1 by omega, pow_succ]
        ring
      rw [hbase]
      rw [hD]
      rw [show a + (s + 1) = a + s + 1 by omega]
      rw [show a + s + 1 + 1 = a + s + 2 by omega]
      rw [show a + s + 2 = (a + s + 1) + 1 by omega, pow_succ]
      ring

theorem factorization_pow_unit_mul_self
    {q k : Nat}
    (hq : Nat.Prime q)
    (hk_ne_zero : k ≠ 0) :
    q ^ (k.factorization q) * (k / q ^ (k.factorization q)) = k := by
  have hpow_dvd : q ^ (k.factorization q) ∣ k := by
    exact (hq.pow_dvd_iff_le_factorization hk_ne_zero).2 le_rfl
  exact Nat.mul_div_cancel' hpow_dvd

theorem odd_prime_order_base_eq_one_add_exact_unit
    {b q d : Nat}
    (hq : Nat.Prime q)
    (hbase_gt_one : 1 < b ^ d) :
    b ^ d =
      1 + q ^ ((b ^ d - 1).factorization q) *
        ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) := by
  have hN_ne_zero : b ^ d - 1 ≠ 0 :=
    Nat.sub_ne_zero_of_lt hbase_gt_one
  have hpow_dvd :
      q ^ ((b ^ d - 1).factorization q) ∣ b ^ d - 1 := by
    exact (hq.pow_dvd_iff_le_factorization hN_ne_zero).2 le_rfl
  have hdecomp :
      q ^ ((b ^ d - 1).factorization q) *
          ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) =
        b ^ d - 1 :=
    Nat.mul_div_cancel' hpow_dvd
  rw [hdecomp]
  omega

theorem odd_prime_order_pow_sub_one_eq_mul_add_pow_succ
    {b q d k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0) :
    ∃ C,
      b ^ (d * k) - 1 =
        q ^ ((b ^ d - 1).factorization q + k.factorization q) *
          (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
            (k / q ^ (k.factorization q))) +
        q ^ (((b ^ d - 1).factorization q + k.factorization q) + 1) * C := by
  let m := (b ^ d - 1).factorization q
  let s := k.factorization q
  let U := (b ^ d - 1) / q ^ m
  let V := k / q ^ s
  have hbase_dvd : q ∣ b ^ d - 1 := by
    have hord : orderOf (ZMod.unitOfCoprime b hcop) ∣ d := by
      rw [hd_order]
    exact (orderOf_dvd_iff_q_dvd_pow_sub_one hcop (le_of_lt hbase_gt_one)).1 hord
  have hN_ne_zero : b ^ d - 1 ≠ 0 :=
    Nat.sub_ne_zero_of_lt hbase_gt_one
  have hm_pos : 0 < m := by
    dsimp [m]
    exact hq.factorization_pos_of_dvd hN_ne_zero hbase_dvd
  have hk_decomp : q ^ s * V = k := by
    dsimp [s, V]
    exact factorization_pow_unit_mul_self hq hk_ne_zero
  have hbase_eq : b ^ d = 1 + q ^ m * U := by
    dsimp [m, U]
    exact odd_prime_order_base_eq_one_add_exact_unit hq hbase_gt_one
  obtain ⟨C, hC⟩ := exists_pow_q_iter_first_order
    (q := q) (a := m) (s := s) (u := U) hq hq_odd hm_pos
  have hms_pos : 0 < m + s := by omega
  obtain ⟨D, hD⟩ := exists_pow_first_order_any_exponent
    (q := q) (r := m + s) (u := U + q * C) (v := V) hq.pos hms_pos
  refine ⟨C * V + D, ?_⟩
  have hpow_eq :
      b ^ (d * k) =
        1 + q ^ (m + s) * (U * V) +
          q ^ ((m + s) + 1) * (C * V + D) := by
    rw [pow_mul]
    rw [← hk_decomp]
    rw [pow_mul]
    rw [hbase_eq]
    rw [hC]
    have hbase2 :
        1 + q ^ (m + s) * U + q ^ (m + s + 1) * C =
          1 + q ^ (m + s) * (U + q * C) := by
      rw [show m + s + 1 = (m + s) + 1 by omega, pow_succ]
      ring
    rw [hbase2]
    rw [hD]
    rw [show m + s + 1 = (m + s) + 1 by omega, pow_succ]
    ring
  dsimp [m, s, U, V] at hpow_eq ⊢
  rw [hpow_eq]
  omega

theorem odd_prime_order_normalized_pow_sub_one_modEq
    {b q d k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0) :
    (b ^ (d * k) - 1) /
        q ^ ((b ^ d - 1).factorization q + k.factorization q)
      ≡
    ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
      (k / q ^ (k.factorization q))
      [MOD q] := by
  obtain ⟨C, hC⟩ := odd_prime_order_pow_sub_one_eq_mul_add_pow_succ
    hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero
  exact exact_pow_div_modEq_of_eq_mul_add_pow_succ hq.pos hC

theorem normalized_factorization_mul_eq
    {q N M D : Nat}
    (hq : Nat.Prime q)
    (hM_ne_zero : M ≠ 0)
    (hD_ne_zero : D ≠ 0)
    (hN_eq : N = M * D) :
    N / q ^ (N.factorization q) =
      (M / q ^ (M.factorization q)) *
        (D / q ^ (D.factorization q)) := by
  have hN_ne_zero : N ≠ 0 := by
    rw [hN_eq]
    exact mul_ne_zero hM_ne_zero hD_ne_zero
  have hv : N.factorization q = M.factorization q + D.factorization q := by
    rw [hN_eq, Nat.factorization_mul hM_ne_zero hD_ne_zero]
    rfl
  have hN_unit := factorization_pow_unit_mul_self hq hN_ne_zero
  have hM_unit := factorization_pow_unit_mul_self hq hM_ne_zero
  have hD_unit := factorization_pow_unit_mul_self hq hD_ne_zero
  have hprod :
      q ^ (N.factorization q) *
          ((M / q ^ (M.factorization q)) *
            (D / q ^ (D.factorization q))) = N := by
    calc
      q ^ (N.factorization q) *
          ((M / q ^ (M.factorization q)) *
            (D / q ^ (D.factorization q)))
          = (q ^ (M.factorization q) * q ^ (D.factorization q)) *
              ((M / q ^ (M.factorization q)) *
                (D / q ^ (D.factorization q))) := by
              rw [hv, pow_add]
      _ = (q ^ (M.factorization q) * (M / q ^ (M.factorization q))) *
              (q ^ (D.factorization q) * (D / q ^ (D.factorization q))) := by
              ring
      _ = M * D := by rw [hM_unit, hD_unit]
      _ = N := by rw [← hN_eq]
  exact Nat.mul_left_cancel (pow_pos hq.pos _) (by rw [hN_unit, hprod])

theorem odd_prime_order_component_term_normalized_crossmul_eq
    {b q d K k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : k ∣ K)
    (hquot_ne_zero :
      ((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) ≠ 0)
    (hden_ne_zero : b ^ (d * k) - 1 ≠ 0) :
    (b ^ (d * K) - 1) /
        q ^ ((b ^ d - 1).factorization q + K.factorization q)
      =
    (((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) /
        q ^ (K.factorization q - k.factorization q)) *
      ((b ^ (d * k) - 1) /
        q ^ ((b ^ d - 1).factorization q + k.factorization q)) := by
  have hdk_dK : d * k ∣ d * K := by
    rcases hkK with ⟨t, rfl⟩
    refine ⟨t, ?_⟩
    ring
  have hN_eq :
      b ^ (d * K) - 1 =
        ((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) *
          (b ^ (d * k) - 1) :=
    pow_sub_one_component_factor b (d * K) (d * k) hdk_dK
  have hNnorm := normalized_factorization_mul_eq
    (q := q)
    (N := b ^ (d * K) - 1)
    (M := (b ^ (d * K) - 1) / (b ^ (d * k) - 1))
    (D := b ^ (d * k) - 1)
    hq hquot_ne_zero hden_ne_zero hN_eq
  have hNval :
      (b ^ (d * K) - 1).factorization q =
        (b ^ d - 1).factorization q + K.factorization q :=
    odd_prime_order_factorization_pow_sub_one
      hq hq_odd hcop hd_order hbase_gt_one hK_ne_zero
  have hDval :
      (b ^ (d * k) - 1).factorization q =
        (b ^ d - 1).factorization q + k.factorization q :=
    odd_prime_order_factorization_pow_sub_one
      hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero
  have hMval :
      ((b ^ (d * K) - 1) / (b ^ (d * k) - 1)).factorization q =
        K.factorization q - k.factorization q :=
    odd_prime_order_component_term_valuation
      hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero hK_ne_zero
      hkK hquot_ne_zero hden_ne_zero
  simpa [hNval, hDval, hMval] using hNnorm

theorem odd_prime_order_component_term_residue_crossmul
    {b q d K k : Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : k ∣ K)
    (hquot_ne_zero :
      ((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) ≠ 0)
    (hden_ne_zero : b ^ (d * k) - 1 ≠ 0) :
    (((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) /
        q ^ (K.factorization q - k.factorization q)) *
      (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
        (k / q ^ (k.factorization q)))
      ≡
    ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
      (K / q ^ (K.factorization q))
      [MOD q] := by
  have hKmod := odd_prime_order_normalized_pow_sub_one_modEq
    (b := b) (q := q) (d := d) (k := K)
    hq hq_odd hcop hd_order hbase_gt_one hK_ne_zero
  have hkmod := odd_prime_order_normalized_pow_sub_one_modEq
    (b := b) (q := q) (d := d) (k := k)
    hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero
  have heq := odd_prime_order_component_term_normalized_crossmul_eq
    (b := b) (q := q) (d := d) (K := K) (k := k)
    hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero hK_ne_zero
    hkK hquot_ne_zero hden_ne_zero
  have hright :
      (((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) /
          q ^ (K.factorization q - k.factorization q)) *
        ((b ^ (d * k) - 1) /
          q ^ ((b ^ d - 1).factorization q + k.factorization q))
        ≡
      ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
        (K / q ^ (K.factorization q))
        [MOD q] := by
    rw [← heq]
    exact hKmod
  have hleft :
      (((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) /
          q ^ (K.factorization q - k.factorization q)) *
        ((b ^ (d * k) - 1) /
          q ^ ((b ^ d - 1).factorization q + k.factorization q))
        ≡
      (((b ^ (d * K) - 1) / (b ^ (d * k) - 1)) /
          q ^ (K.factorization q - k.factorization q)) *
        (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
          (k / q ^ (k.factorization q)))
        [MOD q] := by
    exact Nat.ModEq.mul_left _ hkmod
  exact hleft.symm.trans hright

theorem finset_sum_modEq_of_forall
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {q : Nat}
    {f g : ι → Nat}
    (h : ∀ i, i ∈ s → f i ≡ g i [MOD q]) :
    (∑ i ∈ s, f i) ≡ (∑ i ∈ s, g i) [MOD q] := by
  induction s using Finset.induction_on with
  | empty =>
      exact Nat.ModEq.refl 0
  | insert a s ha ih =>
      simp [ha]
      exact Nat.ModEq.add
        (h a (by simp [ha]))
        (ih (by
          intro i hi
          exact h i (by simp [hi])))

theorem finset_sum_mul_prod_erase_modEq
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {q N : Nat}
    {T D : ι → Nat}
    (h : ∀ i, i ∈ s → T i * D i ≡ N [MOD q]) :
    (∑ i ∈ s, T i) * (∏ i ∈ s, D i)
      ≡
    ∑ i ∈ s, N * (∏ j ∈ s.erase i, D j)
      [MOD q] := by
  have hsum_eq :
      (∑ i ∈ s, T i) * (∏ i ∈ s, D i)
        =
      ∑ i ∈ s, T i * D i * (∏ j ∈ s.erase i, D j) := by
    calc
      (∑ i ∈ s, T i) * (∏ i ∈ s, D i)
          = ∑ i ∈ s, T i * (∏ i ∈ s, D i) := by
              rw [Finset.sum_mul]
      _ = ∑ i ∈ s, T i * (D i * (∏ j ∈ s.erase i, D j)) := by
              refine Finset.sum_congr rfl ?_
              intro i hi
              rw [← Finset.mul_prod_erase s D hi]
      _ = ∑ i ∈ s, T i * D i * (∏ j ∈ s.erase i, D j) := by
              refine Finset.sum_congr rfl ?_
              intro i _hi
              ring
  rw [hsum_eq]
  exact finset_sum_modEq_of_forall (s := s)
    (f := fun i => T i * D i * (∏ j ∈ s.erase i, D j))
    (g := fun i => N * (∏ j ∈ s.erase i, D j))
    (by
      intro i hi
      exact Nat.ModEq.mul_right (∏ j ∈ s.erase i, D j) (h i hi))

theorem odd_prime_order_residue_formula
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {b q d K : Nat}
    {k : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : ∀ i, i ∈ s → k i ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0) :
    (∑ i ∈ s,
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) /
          q ^ (K.factorization q - (k i).factorization q)) *
      (∏ i ∈ s,
        ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
          (k i / q ^ ((k i).factorization q)))
      ≡
    ∑ i ∈ s,
      (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
        (K / q ^ (K.factorization q))) *
        (∏ j ∈ s.erase i,
          ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
            (k j / q ^ ((k j).factorization q)))
      [MOD q] := by
  exact finset_sum_mul_prod_erase_modEq (s := s) (q := q)
    (T := fun i =>
      ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) /
        q ^ (K.factorization q - (k i).factorization q))
    (D := fun i =>
      ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
        (k i / q ^ ((k i).factorization q)))
    (N :=
      ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
        (K / q ^ (K.factorization q)))
    (by
      intro i hi
      exact odd_prime_order_component_term_residue_crossmul
        (b := b) (q := q) (d := d) (K := K) (k := k i)
        hq hq_odd hcop hd_order hbase_gt_one
        (hk_ne_zero i hi) hK_ne_zero (hkK i hi)
        (hquot_ne_zero i hi) (hden_ne_zero i hi))

theorem not_dvd_of_modEq_not_dvd
    {q a b : Nat}
    (hab : a ≡ b [MOD q])
    (hb : ¬ q ∣ b) :
    ¬ q ∣ a := by
  intro ha
  apply hb
  exact (Nat.modEq_zero_iff_dvd).1
    (hab.symm.trans ((Nat.modEq_zero_iff_dvd).2 ha))

theorem not_dvd_sum_of_common_denominator_residue
    {q S P R : Nat}
    (hresidue : S * P ≡ R [MOD q])
    (hR : ¬ q ∣ R) :
    ¬ q ∣ S := by
  intro hS
  exact (not_dvd_of_modEq_not_dvd hresidue hR)
    (dvd_mul_of_dvd_left hS P)

theorem odd_prime_order_residue_formula_not_dvd_sum
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {b q d K : Nat}
    {k : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : ∀ i, i ∈ s → k i ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0)
    (hR_not_dvd :
      ¬ q ∣
        ∑ i ∈ s,
          (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
            (K / q ^ (K.factorization q))) *
            (∏ j ∈ s.erase i,
              ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
                (k j / q ^ ((k j).factorization q)))) :
    ¬ q ∣
      ∑ i ∈ s,
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) /
          q ^ (K.factorization q - (k i).factorization q) := by
  exact not_dvd_sum_of_common_denominator_residue
    (P := ∏ i ∈ s,
      ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
        (k i / q ^ ((k i).factorization q)))
    (R := ∑ i ∈ s,
      (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
        (K / q ^ (K.factorization q))) *
        (∏ j ∈ s.erase i,
          ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
            (k j / q ^ ((k j).factorization q))))
    (odd_prime_order_residue_formula
      (b := b) (q := q) (d := d) (K := K) (k := k)
      hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero hK_ne_zero
      hkK hquot_ne_zero hden_ne_zero)
    hR_not_dvd

theorem collapse_divisor_from_orderOf_component
    {A B Q b d L e : Nat}
    (hcop : Nat.Coprime b Q)
    (hord_dvd : orderOf (ZMod.unitOfCoprime b hcop) ∣ d)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (heL : e ∣ L)
    (hd_e : d ∣ e)
    (hQpos : 0 < Q)
    (hpow : 1 ≤ b ^ d) :
    (b ^ L - 1) / (b ^ e - 1) ∣ A := by
  exact collapse_divisor_from_orderOf_drop
    (A := A)
    (B := B)
    (C := b ^ e - 1)
    (M := (b ^ L - 1) / (b ^ e - 1))
    (Q := Q)
    (b := b)
    (d := d)
    (e := e)
    hcop
    hord_dvd
    hQ
    (by
      rw [hB_eq]
      exact pow_sub_one_component_factor b L e heL)
    rfl
    hd_e
    hQpos
    hpow

theorem quotient_by_pos_divisor_dvd_self
    {L p : Nat}
    (hp_pos : 0 < p)
    (hpL : p ∣ L) :
    L / p ∣ L := by
  rcases hpL with ⟨k, rfl⟩
  rw [mul_comm p k, Nat.mul_div_left _ hp_pos]
  exact dvd_mul_right k p

theorem collapse_divisor_equivalence_one_direction
    {A B Q b d L p : Nat}
    (hp : Nat.Prime p)
    (hpL : p ∣ L)
    (hcop : Nat.Coprime b Q)
    (hord_dvd : orderOf (ZMod.unitOfCoprime b hcop) ∣ d)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hd_drop : d ∣ L / p)
    (hQpos : 0 < Q)
    (hpow : 1 ≤ b ^ d) :
    (b ^ L - 1) / (b ^ (L / p) - 1) ∣ A := by
  exact collapse_divisor_from_orderOf_component
    (A := A)
    (B := B)
    (Q := Q)
    (b := b)
    (d := d)
    (L := L)
    (e := L / p)
    hcop
    hord_dvd
    hQ
    hB_eq
    (quotient_by_pos_divisor_dvd_self hp.pos hpL)
    hd_drop
    hQpos
    hpow

theorem collapse_one_direction_certificate_implies_no_prime_drop
    (d L A B Q b : Nat)
    (q : Nat → Nat)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_dvd : d ∣ L)
    (hQpos : 0 < Q)
    (hcop : Nat.Coprime b Q)
    (hord_dvd : orderOf (ZMod.unitOfCoprime b hcop) ∣ d)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ d)
    (h_q_prime :
      ∀ p, Nat.Prime p → p ∣ L → Nat.Prime (q p))
    (h_M_ne_zero :
      ∀ p, Nat.Prime p → p ∣ L →
        ((b ^ L - 1) / (b ^ (L / p) - 1)) ≠ 0)
    (h_deficit :
      ∀ p, Nat.Prime p → p ∣ L →
        (((b ^ L - 1) / (b ^ (L / p) - 1)).factorization (q p)
          > A.factorization (q p))) :
    d = L := by
  apply valuation_witnesses_imply_no_prime_drop
    d
    L
    A
    (fun p => (b ^ L - 1) / (b ^ (L / p) - 1))
    q
    hLpos
    hA
    h_dvd
  · intro p hp hpL hdrop
    exact collapse_divisor_equivalence_one_direction
      (A := A)
      (B := B)
      (Q := Q)
      (b := b)
      (d := d)
      (L := L)
      (p := p)
      hp
      hpL
      hcop
      hord_dvd
      hQ
      hB_eq
      hdrop
      hQpos
      hpow
  · exact h_q_prime
  · exact h_M_ne_zero
  · exact h_deficit

theorem witness_certificate_implies_period_noncollapse
    (L A B Q b : Nat)
    (q : Nat → Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (h_q_prime :
      ∀ p, Nat.Prime p → p ∣ L → Nat.Prime (q p))
    (h_M_ne_zero :
      ∀ p, Nat.Prime p → p ∣ L →
        ((b ^ L - 1) / (b ^ (L / p) - 1)) ≠ 0)
    (h_deficit :
      ∀ p, Nat.Prime p → p ∣ L →
        (((b ^ L - 1) / (b ^ (L / p) - 1)).factorization (q p)
          > A.factorization (q p))) :
    orderOf (ZMod.unitOfCoprime b hcop) = L := by
  exact collapse_one_direction_certificate_implies_no_prime_drop
    (d := orderOf (ZMod.unitOfCoprime b hcop))
    (L := L)
    (A := A)
    (B := B)
    (Q := Q)
    (b := b)
    (q := q)
    hLpos
    hA
    h_ord_dvd_L
    hQpos
    hcop
    dvd_rfl
    hQ
    hB_eq
    hpow
    h_q_prime
    h_M_ne_zero
    h_deficit

def primeComponentQuotient (b L p : Nat) : Nat :=
  (b ^ L - 1) / (b ^ (L / p) - 1)

def PrimeComponentWitness
    (L A b p q : Nat) : Prop :=
  Nat.Prime q ∧
    primeComponentQuotient b L p ≠ 0 ∧
    (primeComponentQuotient b L p).factorization q > A.factorization q

theorem primeComponentWitness_of_prime_power_cofactor
    (L A b p q quotient exponent reducedCofactor AExponent : Nat)
    (hq : Nat.Prime q)
    (hquot : primeComponentQuotient b L p = quotient)
    (hfactor : quotient = q ^ exponent * reducedCofactor)
    (hquot_ne_zero : quotient ≠ 0)
    (hA_factor : A.factorization q = AExponent)
    (hsurplus : AExponent < exponent) :
    PrimeComponentWitness L A b p q := by
  refine ⟨hq, ?_, ?_⟩
  · rw [hquot]
    exact hquot_ne_zero
  · rw [hquot, hA_factor]
    have hpow_dvd : q ^ exponent ∣ quotient := by
      rw [hfactor]
      exact dvd_mul_right _ _
    have hle : exponent ≤ quotient.factorization q := by
      simpa using (hq.pow_dvd_iff_le_factorization hquot_ne_zero).mp hpow_dvd
    exact lt_of_lt_of_le hsurplus hle

theorem PrimeComponentWitness.mul_right_of_factorization_eq_zero
    {L A b p q k : Nat}
    (hwit : PrimeComponentWitness L A b p q)
    (hA : A ≠ 0)
    (hk : k ≠ 0)
    (hkq : k.factorization q = 0) :
    PrimeComponentWitness L (A * k) b p q := by
  rcases hwit with ⟨hq, hquot_ne_zero, hdeficit⟩
  refine ⟨hq, hquot_ne_zero, ?_⟩
  rw [Nat.factorization_mul hA hk]
  simpa [hkq] using hdeficit

theorem PrimeComponentWitness.of_factorization_le
    {L A A' b p q : Nat}
    (hwit : PrimeComponentWitness L A b p q)
    (hle : A'.factorization q ≤ A.factorization q) :
    PrimeComponentWitness L A' b p q := by
  rcases hwit with ⟨hq, hquot_ne_zero, hdeficit⟩
  refine ⟨hq, hquot_ne_zero, ?_⟩
  exact lt_of_le_of_lt hle hdeficit

noncomputable def canonicalPrimeComponentWitness
    (L A b p : Nat)
    (hex : ∃ q, PrimeComponentWitness L A b p q) : Nat := by
  classical
  exact Nat.find hex

theorem canonicalPrimeComponentWitness_spec
    (L A b p : Nat)
    (hex : ∃ q, PrimeComponentWitness L A b p q) :
    PrimeComponentWitness L A b p
      (canonicalPrimeComponentWitness L A b p hex) := by
  classical
  simpa [canonicalPrimeComponentWitness] using (Nat.find_spec hex)

theorem canonicalPrimeComponentWitness_minimal
    (L A b p q : Nat)
    (hex : ∃ q, PrimeComponentWitness L A b p q)
    (hq : PrimeComponentWitness L A b p q) :
    canonicalPrimeComponentWitness L A b p hex ≤ q := by
  classical
  simpa [canonicalPrimeComponentWitness] using (Nat.find_min' hex hq)

theorem witness_existence_implies_period_noncollapse
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (h_exists :
      ∀ p, Nat.Prime p → p ∣ L →
        ∃ q, PrimeComponentWitness L A b p q) :
    orderOf (ZMod.unitOfCoprime b hcop) = L := by
  classical
  let q : Nat → Nat := fun p =>
    if h : Nat.Prime p ∧ p ∣ L then
      canonicalPrimeComponentWitness L A b p (h_exists p h.1 h.2)
    else
      0
  apply witness_certificate_implies_period_noncollapse
    (L := L)
    (A := A)
    (B := B)
    (Q := Q)
    (b := b)
    (q := q)
    hcop
    hLpos
    hA
    h_ord_dvd_L
    hQpos
    hQ
    hB_eq
    hpow
  · intro p hp hpL
    have hs :
        PrimeComponentWitness L A b p (q p) := by
      dsimp [q]
      rw [dif_pos ⟨hp, hpL⟩]
      exact canonicalPrimeComponentWitness_spec
        L A b p (h_exists p hp hpL)
    exact hs.1
  · intro p hp hpL
    have hs :
        PrimeComponentWitness L A b p (q p) := by
      dsimp [q]
      rw [dif_pos ⟨hp, hpL⟩]
      exact canonicalPrimeComponentWitness_spec
        L A b p (h_exists p hp hpL)
    simpa [primeComponentQuotient] using hs.2.1
  · intro p hp hpL
    have hs :
        PrimeComponentWitness L A b p (q p) := by
      dsimp [q]
      rw [dif_pos ⟨hp, hpL⟩]
      exact canonicalPrimeComponentWitness_spec
        L A b p (h_exists p hp hpL)
    simpa [primeComponentQuotient] using hs.2.2

def LocalLayerCertificate
    {ι : Type*}
    (s : Finset ι)
    (q m : Nat)
    (T : ι → Nat) : Prop :=
  Nat.Prime q ∧
    (∀ i, i ∈ s → q ^ m ∣ T i) ∧
    ¬ q ∣ ∑ i ∈ s, T i / q ^ m

theorem local_layer_residue_nonzero_implies_sum_valuation
    {ι : Type*}
    (s : Finset ι)
    (q m : Nat)
    (T : ι → Nat)
    (hq : Nat.Prime q)
    (hdvd : ∀ i, i ∈ s → q ^ m ∣ T i)
    (hres : ¬ q ∣ ∑ i ∈ s, T i / q ^ m) :
    (∑ i ∈ s, T i).factorization q = m := by
  have hq_pos : 0 < q := hq.pos
  have hq_pow_pos : 0 < q ^ m := pow_pos hq_pos m
  have hq_pow_ne_zero : q ^ m ≠ 0 := Nat.pos_iff_ne_zero.mp hq_pow_pos
  have hsum_eq :
      ∑ i ∈ s, T i = q ^ m * (∑ i ∈ s, T i / q ^ m) := by
    rw [Finset.mul_sum]
    refine Finset.sum_congr rfl ?_
    intro i hi
    exact (Nat.mul_div_cancel' (hdvd i hi)).symm
  have hR_ne_zero : (∑ i ∈ s, T i / q ^ m) ≠ 0 := by
    intro hR_zero
    exact hres (hR_zero ▸ dvd_zero q)
  rw [hsum_eq, Nat.factorization_mul hq_pow_ne_zero hR_ne_zero]
  simp [Nat.factorization_eq_zero_of_not_dvd hres,
        Nat.Prime.factorization_pow hq]

theorem LocalLayerCertificate.sum_factorization
    {ι : Type*}
    {s : Finset ι}
    {q m : Nat}
    {T : ι → Nat}
    (cert : LocalLayerCertificate s q m T) :
    (∑ i ∈ s, T i).factorization q = m :=
  local_layer_residue_nonzero_implies_sum_valuation
    s q m T cert.1 cert.2.1 cert.2.2

theorem LocalLayerCertificate.of_q_pow_decomposition
    {ι : Type*}
    {s : Finset ι}
    {q m : Nat}
    {T R : ι → Nat}
    (hq : Nat.Prime q)
    (hT :
      ∀ i, i ∈ s → T i = q ^ m * R i)
    (hres :
      ¬ q ∣ ∑ i ∈ s, R i) :
    LocalLayerCertificate s q m T := by
  refine ⟨hq, ?_, ?_⟩
  · intro i hi
    refine ⟨R i, ?_⟩
    exact hT i hi
  · have hsum :
        (∑ i ∈ s, T i / q ^ m) = ∑ i ∈ s, R i := by
      refine Finset.sum_congr rfl ?_
      intro i hi
      rw [hT i hi]
      exact Nat.mul_div_cancel_left (R i) (pow_pos hq.pos m)
    rwa [hsum]

theorem not_dvd_sum_of_subset_complement_dvd
    {ι : Type*}
    [DecidableEq ι]
    {s t : Finset ι}
    {q : Nat}
    {R : ι → Nat}
    (hts : t ⊆ s)
    (hhigh :
      ∀ i, i ∈ s → i ∉ t → q ∣ R i)
    (hres_min :
      ¬ q ∣ ∑ i ∈ t, R i) :
    ¬ q ∣ ∑ i ∈ s, R i := by
  have hfilter_eq : s.filter (fun i => i ∈ t) = t := by
    ext i
    by_cases hit : i ∈ t
    · simp [hit, hts hit]
    · simp [hit]
  have hsplit :
      (∑ i ∈ t, R i) +
          (∑ i ∈ s.filter (fun i => i ∉ t), R i) =
        ∑ i ∈ s, R i := by
    simpa [hfilter_eq] using
      (Finset.sum_filter_add_sum_filter_not s (fun i => i ∈ t) R)
  have hhigh_sum :
      q ∣ ∑ i ∈ s.filter (fun i => i ∉ t), R i := by
    refine Finset.dvd_sum ?_
    intro i hi
    rcases Finset.mem_filter.mp hi with ⟨his, hit⟩
    exact hhigh i his hit
  intro hfull
  exact hres_min <| by
    apply (Nat.dvd_add_iff_left hhigh_sum).2
    rwa [hsplit]

theorem not_dvd_sum_of_singleton_unit_and_complement_dvd
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q : Nat}
    {R : ι → Nat}
    (hi0 : i0 ∈ s)
    (hunit : ¬ q ∣ R i0)
    (hrest :
      ∀ i, i ∈ s → i ≠ i0 → q ∣ R i) :
    ¬ q ∣ ∑ i ∈ s, R i := by
  refine not_dvd_sum_of_subset_complement_dvd
    (s := s) (t := ({i0} : Finset ι)) (q := q) (R := R)
    ?hts ?hhigh ?hres_min
  · intro i hi
    rw [Finset.mem_singleton] at hi
    simpa [hi] using hi0
  · intro i hi hit
    exact hrest i hi (by
      intro h_eq
      apply hit
      simp [h_eq])
  · simpa using hunit

theorem residue_formula_singleton_nonzero_certificate
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q commonResidue : Nat}
    {D : ι → Nat}
    (hi0 : i0 ∈ s)
    (hunit :
      ¬ q ∣ commonResidue * (∏ j ∈ s.erase i0, D j))
    (hrest :
      ∀ i, i ∈ s → i ≠ i0 →
        q ∣ commonResidue * (∏ j ∈ s.erase i, D j)) :
    ¬ q ∣ ∑ i ∈ s, commonResidue * (∏ j ∈ s.erase i, D j) := by
  exact not_dvd_sum_of_singleton_unit_and_complement_dvd
    (s := s)
    (i0 := i0)
    (q := q)
    (R := fun i => commonResidue * (∏ j ∈ s.erase i, D j))
    hi0 hunit hrest

theorem LocalLayerCertificate.of_minimal_layer_decomposition
    {ι : Type*}
    [DecidableEq ι]
    {s t : Finset ι}
    {q m : Nat}
    {T R : ι → Nat}
    (hq : Nat.Prime q)
    (hts : t ⊆ s)
    (hT :
      ∀ i, i ∈ s → T i = q ^ m * R i)
    (hhigh :
      ∀ i, i ∈ s → i ∉ t → q ∣ R i)
    (hres_min :
      ¬ q ∣ ∑ i ∈ t, R i) :
    LocalLayerCertificate s q m T := by
  refine LocalLayerCertificate.of_q_pow_decomposition hq hT ?_
  exact not_dvd_sum_of_subset_complement_dvd hts hhigh hres_min

theorem local_layer_certificate_supplies_PrimeComponentWitness
    {L A b p q : Nat}
    (hprime : Nat.Prime q)
    (hquot_ne_zero : primeComponentQuotient b L p ≠ 0)
    (hdef : A.factorization q < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q :=
  ⟨hprime, hquot_ne_zero, hdef⟩

theorem local_layer_sum_certificate_supplies_PrimeComponentWitness
    {ι : Type*}
    {s : Finset ι}
    {q m L A b p : Nat}
    {T : ι → Nat}
    (cert : LocalLayerCertificate s q m T)
    (hA_eq : A = ∑ i ∈ s, T i)
    (hquot_ne_zero : primeComponentQuotient b L p ≠ 0)
    (hMval : m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q := by
  have hAval : A.factorization q = m := by
    rw [hA_eq]
    exact LocalLayerCertificate.sum_factorization cert
  refine local_layer_certificate_supplies_PrimeComponentWitness
    cert.1 hquot_ne_zero ?_
  rw [hAval]
  exact hMval

theorem local_layer_decomposition_supplies_PrimeComponentWitness
    {ι : Type*}
    {s : Finset ι}
    {q m L A b p : Nat}
    {T R : ι → Nat}
    (hq : Nat.Prime q)
    (hT :
      ∀ i, i ∈ s → T i = q ^ m * R i)
    (hres :
      ¬ q ∣ ∑ i ∈ s, R i)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q :=
  local_layer_sum_certificate_supplies_PrimeComponentWitness
    (LocalLayerCertificate.of_q_pow_decomposition hq hT hres)
    hA_eq
    hquot_ne_zero
    hMval

theorem minimal_layer_decomposition_supplies_PrimeComponentWitness
    {ι : Type*}
    [DecidableEq ι]
    {s t : Finset ι}
    {q m L A b p : Nat}
    {T R : ι → Nat}
    (hq : Nat.Prime q)
    (hts : t ⊆ s)
    (hT :
      ∀ i, i ∈ s → T i = q ^ m * R i)
    (hhigh :
      ∀ i, i ∈ s → i ∉ t → q ∣ R i)
    (hres_min :
      ¬ q ∣ ∑ i ∈ t, R i)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q :=
  local_layer_sum_certificate_supplies_PrimeComponentWitness
    (LocalLayerCertificate.of_minimal_layer_decomposition
      hq hts hT hhigh hres_min)
    hA_eq
    hquot_ne_zero
    hMval

theorem singleton_minimal_layer_row_supplies_PrimeComponentWitness
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q m L A b p : Nat}
    {T R : ι → Nat}
    (hq : Nat.Prime q)
    (hi0 : i0 ∈ s)
    (hT :
      ∀ i, i ∈ s → T i = q ^ m * R i)
    (hhigh :
      ∀ i, i ∈ s → i ≠ i0 → q ∣ R i)
    (hres :
      ¬ q ∣ R i0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q := by
  refine minimal_layer_decomposition_supplies_PrimeComponentWitness
    (s := s)
    (t := ({i0} : Finset ι))
    (q := q)
    (m := m)
    (L := L)
    (A := A)
    (b := b)
    (p := p)
    (T := T)
    (R := R)
    hq ?hts hT ?hhigh_min ?hres_min hA_eq hquot_ne_zero hMval
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    exact hi0
  · intro i hi hit
    exact hhigh i hi (by
      intro h_eq
      apply hit
      simp [h_eq])
  · simpa using hres

theorem singleton_minimal_layer_row_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q m L A b p : Nat}
    {T R : ι → Nat}
    (hq : Nat.Prime q)
    (hi0 : i0 ∈ s)
    (hT :
      ∀ i, i ∈ s → T i = q ^ m * R i)
    (hhigh :
      ∀ i, i ∈ s → i ≠ i0 → q ∣ R i)
    (hres :
      ¬ q ∣ R i0)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hW : PrimeComponentWitness L A b p q :=
    singleton_minimal_layer_row_supplies_PrimeComponentWitness
      (s := s)
      (i0 := i0)
      (q := q)
      (m := m)
      (L := L)
      (A := A)
      (b := b)
      (p := p)
      (T := T)
      (R := R)
      hq hi0 hT hhigh hres hA_eq hquot_ne_zero hMval
  exact valuation_deficit_blocks_dvd hW.1 hW.2.1 hA hW.2.2

theorem dvd_div_pow_of_lt_factorization
    {q N m : Nat}
    (hq : Nat.Prime q)
    (hN_ne_zero : N ≠ 0)
    (hm : m < N.factorization q) :
    q ∣ N / q ^ m := by
  have hsucc_le : m + 1 ≤ N.factorization q := by omega
  have hpow_succ_dvd : q ^ (m + 1) ∣ N :=
    (hq.pow_dvd_iff_le_factorization hN_ne_zero).2 hsucc_le
  rcases hpow_succ_dvd with ⟨t, ht⟩
  refine ⟨t, ?_⟩
  rw [ht]
  rw [show q ^ (m + 1) = q ^ m * q by rw [pow_succ]]
  rw [Nat.mul_assoc]
  exact Nat.mul_div_cancel_left (q * t) (pow_pos hq.pos m)

theorem not_dvd_div_pow_of_factorization_eq
    {q N m : Nat}
    (hq : Nat.Prime q)
    (hN_ne_zero : N ≠ 0)
    (hm : N.factorization q = m) :
    ¬ q ∣ N / q ^ m := by
  simpa [hm] using
    (normalized_factorization_unit_not_dvd
      (q := q)
      (N := N)
      hq
      hN_ne_zero)

theorem singleton_minimal_factorization_row_supplies_PrimeComponentWitness
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q m L A b p : Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hi0 : i0 ∈ s)
    (hT_ne_zero :
      ∀ i, i ∈ s → T i ≠ 0)
    (hi0_val :
      (T i0).factorization q = m)
    (hhigh_val :
      ∀ i, i ∈ s → i ≠ i0 → m < (T i).factorization q)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q := by
  refine singleton_minimal_layer_row_supplies_PrimeComponentWitness
    (s := s)
    (i0 := i0)
    (q := q)
    (m := m)
    (L := L)
    (A := A)
    (b := b)
    (p := p)
    (T := T)
    (R := fun i => T i / q ^ m)
    hq hi0 ?hT ?hhigh ?hres hA_eq hquot_ne_zero hMval
  · intro i hi
    have hdiv : q ^ m ∣ T i := by
      by_cases h_eq : i = i0
      · subst i
        exact (hq.pow_dvd_iff_le_factorization (hT_ne_zero i0 hi0)).2
          (by rw [hi0_val])
      · exact (hq.pow_dvd_iff_le_factorization (hT_ne_zero i hi)).2
          (le_of_lt (hhigh_val i hi h_eq))
    exact (Nat.mul_div_cancel' hdiv).symm
  · intro i hi hne
    exact dvd_div_pow_of_lt_factorization
      hq
      (hT_ne_zero i hi)
      (hhigh_val i hi hne)
  · exact not_dvd_div_pow_of_factorization_eq
      hq
      (hT_ne_zero i0 hi0)
      hi0_val

theorem singleton_minimal_factorization_row_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q m L A b p : Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hi0 : i0 ∈ s)
    (hT_ne_zero :
      ∀ i, i ∈ s → T i ≠ 0)
    (hi0_val :
      (T i0).factorization q = m)
    (hhigh_val :
      ∀ i, i ∈ s → i ≠ i0 → m < (T i).factorization q)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hW : PrimeComponentWitness L A b p q :=
    singleton_minimal_factorization_row_supplies_PrimeComponentWitness
      (s := s)
      (i0 := i0)
      (q := q)
      (m := m)
      (L := L)
      (A := A)
      (b := b)
      (p := p)
      (T := T)
      hq hi0 hT_ne_zero hi0_val hhigh_val hA_eq hquot_ne_zero hMval
  exact valuation_deficit_blocks_dvd hW.1 hW.2.1 hA hW.2.2

theorem primitive_witness_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q m L A b p : Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hi0 : i0 ∈ s)
    (hT_ne_zero :
      ∀ i, i ∈ s → T i ≠ 0)
    (hi0_val :
      (T i0).factorization q = m)
    (hhigh_val :
      ∀ i, i ∈ s → i ≠ i0 → m < (T i).factorization q)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A :=
  singleton_minimal_factorization_row_blocks_collapse
    (s := s)
    (i0 := i0)
    (q := q)
    (m := m)
    (L := L)
    (A := A)
    (b := b)
    (p := p)
    (T := T)
    hq hi0 hT_ne_zero hi0_val hhigh_val hA hA_eq hquot_ne_zero hMval

theorem sub_lt_sub_of_lt_right_with_le
    {A x y : Nat}
    (hyx : y < x)
    (hxA : x ≤ A) :
    A - x < A - y := by
  omega

theorem maximal_weight_factorization_row_supplies_PrimeComponentWitness
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q M m L A b p : Nat}
    {T : ι → Nat}
    {w : ι → Nat}
    (hq : Nat.Prime q)
    (hi0 : i0 ∈ s)
    (hT_ne_zero :
      ∀ i, i ∈ s → T i ≠ 0)
    (hrow_val :
      ∀ i, i ∈ s → (T i).factorization q = M - w i)
    (hi0_le :
      w i0 ≤ M)
    (hm :
      m = M - w i0)
    (hstrict_max :
      ∀ i, i ∈ s → i ≠ i0 → w i < w i0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q := by
  refine singleton_minimal_factorization_row_supplies_PrimeComponentWitness
    (s := s)
    (i0 := i0)
    (q := q)
    (m := m)
    (L := L)
    (A := A)
    (b := b)
    (p := p)
    (T := T)
    hq hi0 hT_ne_zero ?hi0_val ?hhigh_val hA_eq hquot_ne_zero hMval
  · rw [hrow_val i0 hi0, hm]
  · intro i hi hne
    rw [hrow_val i hi, hm]
    exact sub_lt_sub_of_lt_right_with_le (hstrict_max i hi hne) hi0_le

theorem maximal_weight_factorization_row_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {q M m L A b p : Nat}
    {T : ι → Nat}
    {w : ι → Nat}
    (hq : Nat.Prime q)
    (hi0 : i0 ∈ s)
    (hT_ne_zero :
      ∀ i, i ∈ s → T i ≠ 0)
    (hrow_val :
      ∀ i, i ∈ s → (T i).factorization q = M - w i)
    (hi0_le :
      w i0 ≤ M)
    (hm :
      m = M - w i0)
    (hstrict_max :
      ∀ i, i ∈ s → i ≠ i0 → w i < w i0)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hquot_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hW : PrimeComponentWitness L A b p q :=
    maximal_weight_factorization_row_supplies_PrimeComponentWitness
      (s := s)
      (i0 := i0)
      (q := q)
      (M := M)
      (m := m)
      (L := L)
      (A := A)
      (b := b)
      (p := p)
      (T := T)
      (w := w)
      hq hi0 hT_ne_zero hrow_val hi0_le hm hstrict_max hA_eq
      hquot_ne_zero hMval
  exact valuation_deficit_blocks_dvd hW.1 hW.2.1 hA hW.2.2

theorem component_term_maximal_row_supplies_PrimeComponentWitness
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b q d K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hi0 : i0 ∈ s)
    (hK_ne_zero : K ≠ 0)
    (hk_ne_zero :
      ∀ i, i ∈ s → k i ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ (d * K) - 1) / (b ^ (d * k i) - 1))
    (hweight_le :
      ∀ i, i ∈ s → (k i).factorization q ≤ K.factorization q)
    (hm :
      m = K.factorization q - (k i0).factorization q)
    (hstrict_max :
      ∀ i, i ∈ s → i ≠ i0 →
        (k i).factorization q < (k i0).factorization q)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q := by
  refine maximal_weight_factorization_row_supplies_PrimeComponentWitness
    (s := s)
    (i0 := i0)
    (q := q)
    (M := K.factorization q)
    (m := m)
    (L := L)
    (A := A)
    (b := b)
    (p := p)
    (T := T)
    (w := fun i => (k i).factorization q)
    hq hi0 ?hT_ne_zero ?hrow_val (hweight_le i0 hi0) hm hstrict_max
    hA_eq hpcq_ne_zero hMval
  · intro i hi
    rw [hT i hi]
    exact hquot_ne_zero_rows i hi
  · intro i hi
    rw [hT i hi]
    exact odd_prime_order_component_term_valuation
      (b := b)
      (q := q)
      (d := d)
      (K := K)
      (k := k i)
      hq
      hq_odd
      hcop
      hd_order
      hbase_gt_one
      (hk_ne_zero i hi)
      hK_ne_zero
      (hkK i hi)
      (hquot_ne_zero_rows i hi)
      (hden_ne_zero i hi)

theorem component_term_maximal_row_supplies_PrimeComponentWitness_of_dvd
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b q d K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hi0 : i0 ∈ s)
    (hK_ne_zero : K ≠ 0)
    (hk_ne_zero :
      ∀ i, i ∈ s → k i ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ (d * K) - 1) / (b ^ (d * k i) - 1))
    (hm :
      m = K.factorization q - (k i0).factorization q)
    (hstrict_max :
      ∀ i, i ∈ s → i ≠ i0 →
        (k i).factorization q < (k i0).factorization q)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q := by
  exact component_term_maximal_row_supplies_PrimeComponentWitness
    (s := s)
    (i0 := i0)
    (b := b)
    (q := q)
    (d := d)
    (K := K)
    (m := m)
    (L := L)
    (A := A)
    (p := p)
    (k := k)
    (T := T)
    hq hq_odd hcop hd_order hbase_gt_one hi0 hK_ne_zero hk_ne_zero
    hkK hquot_ne_zero_rows hden_ne_zero hT
    (fun i hi => factorization_le_of_dvd_ne_zero hK_ne_zero (hkK i hi))
    hm hstrict_max hA_eq hpcq_ne_zero hMval

theorem component_term_maximal_row_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b q d K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hi0 : i0 ∈ s)
    (hK_ne_zero : K ≠ 0)
    (hk_ne_zero :
      ∀ i, i ∈ s → k i ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ (d * K) - 1) / (b ^ (d * k i) - 1))
    (hweight_le :
      ∀ i, i ∈ s → (k i).factorization q ≤ K.factorization q)
    (hm :
      m = K.factorization q - (k i0).factorization q)
    (hstrict_max :
      ∀ i, i ∈ s → i ≠ i0 →
        (k i).factorization q < (k i0).factorization q)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hW : PrimeComponentWitness L A b p q :=
    component_term_maximal_row_supplies_PrimeComponentWitness
      (s := s)
      (i0 := i0)
      (b := b)
      (q := q)
      (d := d)
      (K := K)
      (m := m)
      (L := L)
      (A := A)
      (p := p)
      (k := k)
      (T := T)
      hq hq_odd hcop hd_order hbase_gt_one hi0 hK_ne_zero hk_ne_zero
      hkK hquot_ne_zero_rows hden_ne_zero hT hweight_le hm hstrict_max
      hA_eq hpcq_ne_zero hMval
  exact valuation_deficit_blocks_dvd hW.1 hW.2.1 hA hW.2.2

theorem odd_component_canonical_row_supplies_PrimeComponentWitness
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b q d K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hi0 : i0 ∈ s)
    (hK_ne_zero : K ≠ 0)
    (hk_ne_zero :
      ∀ i, i ∈ s → k i ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ (d * K) - 1) / (b ^ (d * k i) - 1))
    (hm :
      m = K.factorization q - (k i0).factorization q)
    (hstrict_max :
      ∀ i, i ∈ s → i ≠ i0 →
        (k i).factorization q < (k i0).factorization q)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    PrimeComponentWitness L A b p q := by
  exact component_term_maximal_row_supplies_PrimeComponentWitness_of_dvd
    (s := s)
    (i0 := i0)
    (b := b)
    (q := q)
    (d := d)
    (K := K)
    (m := m)
    (L := L)
    (A := A)
    (p := p)
    (k := k)
    (T := T)
    hq hq_odd hcop hd_order hbase_gt_one hi0 hK_ne_zero hk_ne_zero
    hkK hquot_ne_zero_rows hden_ne_zero hT hm hstrict_max hA_eq
    hpcq_ne_zero hMval

theorem odd_component_canonical_row_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b q d K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hi0 : i0 ∈ s)
    (hK_ne_zero : K ≠ 0)
    (hk_ne_zero :
      ∀ i, i ∈ s → k i ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ (d * K) - 1) / (b ^ (d * k i) - 1))
    (hm :
      m = K.factorization q - (k i0).factorization q)
    (hstrict_max :
      ∀ i, i ∈ s → i ≠ i0 →
        (k i).factorization q < (k i0).factorization q)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hW : PrimeComponentWitness L A b p q :=
    odd_component_canonical_row_supplies_PrimeComponentWitness
      (s := s)
      (i0 := i0)
      (b := b)
      (q := q)
      (d := d)
      (K := K)
      (m := m)
      (L := L)
      (A := A)
      (p := p)
      (k := k)
      (T := T)
      hq hq_odd hcop hd_order hbase_gt_one hi0 hK_ne_zero hk_ne_zero
      hkK hquot_ne_zero_rows hden_ne_zero hT hm hstrict_max hA_eq
      hpcq_ne_zero hMval
  exact valuation_deficit_blocks_dvd hW.1 hW.2.1 hA hW.2.2

theorem two_adic_pow_sub_one_factorization_even
    {b n : Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hn_ne_zero : n ≠ 0)
    (hn_even : Even n) :
    (b ^ n - 1).factorization 2 + 1 =
      (b + 1).factorization 2 +
      (b - 1).factorization 2 +
      n.factorization 2 := by
  rw [Nat.factorization_def (b ^ n - 1) Nat.prime_two]
  rw [Nat.factorization_def (b + 1) Nat.prime_two]
  rw [Nat.factorization_def (b - 1) Nat.prime_two]
  rw [Nat.factorization_def n Nat.prime_two]
  exact padicValNat.pow_two_sub_one
    hb_gt_one
    (by
      intro h
      exact (Nat.not_even_iff_odd.mpr hb_odd) ((even_iff_two_dvd).2 h))
    hn_ne_zero
    hn_even

theorem two_adic_pow_sub_one_factorization_odd
    {b k : Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hk_ne_zero : k ≠ 0)
    (hk_odd : Odd k) :
    (b ^ k - 1).factorization 2 =
      (b - 1).factorization 2 := by
  rw [Nat.factorization_def (b ^ k - 1) Nat.prime_two]
  rw [Nat.factorization_def (b - 1) Nat.prime_two]
  apply ENat.coe_inj.mp
  have hpow_gt_one : 1 < b ^ k := Nat.one_lt_pow hk_ne_zero hb_gt_one
  have hpow_ne_zero : b ^ k - 1 ≠ 0 := Nat.sub_ne_zero_of_lt hpow_gt_one
  have hbase_ne_zero : b - 1 ≠ 0 := Nat.sub_ne_zero_of_lt hb_gt_one
  rw [padicValNat_eq_emultiplicity (p := 2) hpow_ne_zero]
  rw [padicValNat_eq_emultiplicity (p := 2) hbase_ne_zero]
  rw [← Int.natCast_emultiplicity 2 (b ^ k - 1)]
  rw [← Int.natCast_emultiplicity 2 (b - 1)]
  have hxy_nat : 2 ∣ b - 1 :=
    even_iff_two_dvd.mp (Nat.Odd.sub_odd hb_odd odd_one)
  have hxy_int : (2 : Int) ∣ (b : Int) - 1 := by
    have hcast : (2 : Int) ∣ ((b - 1 : Nat) : Int) :=
      (Int.natCast_dvd_natCast).2 hxy_nat
    simpa [Int.ofNat_sub (Nat.le_of_lt hb_gt_one)] using hcast
  have hx_int : ¬ (2 : Int) ∣ (b : Int) := by
    intro h
    exact (Nat.not_even_iff_odd.mpr hb_odd)
      ((even_iff_two_dvd).2 ((Int.natCast_dvd_natCast).1 h))
  have hk_int : ¬ (2 : Int) ∣ (k : Int) := by
    intro h
    exact (Nat.not_even_iff_odd.mpr hk_odd)
      ((even_iff_two_dvd).2 ((Int.natCast_dvd_natCast).1 h))
  have hpow_le : 1 ≤ b ^ k := Nat.le_of_lt hpow_gt_one
  have hbase_le : 1 ≤ b := Nat.le_of_lt hb_gt_one
  have hval :
      emultiplicity (2 : Int) ((b : Int) ^ k - (1 : Int) ^ k) =
        emultiplicity (2 : Int) ((b : Int) - (1 : Int)) := by
    exact emultiplicity_pow_sub_pow_of_prime
      (R := Int)
      (p := (2 : Int))
      ((Nat.prime_iff_prime_int).1 Nat.prime_two)
      (x := (b : Int))
      (y := (1 : Int))
      hxy_int
      hx_int
      (n := k)
      hk_int
  simpa [Int.ofNat_sub hpow_le, Int.ofNat_sub hbase_le, Int.natCast_pow] using hval

theorem two_adic_n0_2_selected_component_valuation
    {b K : Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hK_ne_zero : K ≠ 0)
    (hK_even : Even K)
    (h2K : 2 ∣ K)
    (hquot_ne_zero : ((b ^ K - 1) / (b ^ 2 - 1)) ≠ 0)
    (hden_ne_zero : b ^ 2 - 1 ≠ 0) :
    (((b ^ K - 1) / (b ^ 2 - 1)).factorization 2)
      = K.factorization 2 - 1 := by
  have hquot :
      (((b ^ K - 1) / (b ^ 2 - 1)).factorization 2)
        = (b ^ K - 1).factorization 2 - (b ^ 2 - 1).factorization 2 :=
    pow_sub_one_component_factorization
      (b := b)
      (L := K)
      (e := 2)
      (q := 2)
      h2K
      hquot_ne_zero
      hden_ne_zero
  have hnum := two_adic_pow_sub_one_factorization_even
    (b := b) (n := K) hb_gt_one hb_odd hK_ne_zero hK_even
  have hden := two_adic_pow_sub_one_factorization_even
    (b := b) (n := 2) hb_gt_one hb_odd (by decide) (by decide)
  have htwo : (2 : Nat).factorization 2 = 1 := by
    exact Nat.Prime.factorization_self Nat.prime_two
  rw [hquot]
  rw [htwo] at hden
  omega

theorem two_adic_n0_2_exception_supplies_PrimeComponentWitness
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hi0 : i0 ∈ s)
    (hi0_k : k i0 = 2)
    (hK_ne_zero : K ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ K - 1) / (b ^ k i - 1)) ≠ 0)
    (hden_ne_zero : b ^ 2 - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ K - 1) / (b ^ k i - 1))
    (hm :
      m = K.factorization 2 - 1)
    (hhigh_val :
      ∀ i, i ∈ s → i ≠ i0 → m < (T i).factorization 2)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization 2) :
    PrimeComponentWitness L A b p 2 := by
  refine singleton_minimal_factorization_row_supplies_PrimeComponentWitness
    (s := s)
    (i0 := i0)
    (q := 2)
    (m := m)
    (L := L)
    (A := A)
    (b := b)
    (p := p)
    (T := T)
    Nat.prime_two hi0 ?hT_ne_zero ?hi0_val hhigh_val hA_eq hpcq_ne_zero hMval
  · intro i hi
    rw [hT i hi]
    exact hquot_ne_zero_rows i hi
  · rw [hT i0 hi0, hi0_k]
    have h2K : 2 ∣ K := by
      simpa [hi0_k] using hkK i0 hi0
    have hK_even : Even K := (even_iff_two_dvd).2 h2K
    rw [hm]
    exact two_adic_n0_2_selected_component_valuation
      hb_gt_one hb_odd hK_ne_zero hK_even h2K
      (by simpa [hi0_k] using hquot_ne_zero_rows i0 hi0)
      hden_ne_zero

theorem two_adic_n0_2_odd_row_component_valuation_plus_one
    {b K k : Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hK_ne_zero : K ≠ 0)
    (h2K : 2 ∣ K)
    (hk_ne_zero : k ≠ 0)
    (hk_odd : Odd k)
    (hkK : k ∣ K)
    (hquot_ne_zero : ((b ^ K - 1) / (b ^ k - 1)) ≠ 0) :
    (((b ^ K - 1) / (b ^ k - 1)).factorization 2) + 1 =
      (b + 1).factorization 2 + K.factorization 2 := by
  have hK_even : Even K := (even_iff_two_dvd).2 h2K
  have hden_ne_zero : b ^ k - 1 ≠ 0 :=
    Nat.sub_ne_zero_of_lt (Nat.one_lt_pow hk_ne_zero hb_gt_one)
  have hquot :
      (((b ^ K - 1) / (b ^ k - 1)).factorization 2)
        = (b ^ K - 1).factorization 2 - (b ^ k - 1).factorization 2 :=
    pow_sub_one_component_factorization
      (b := b)
      (L := K)
      (e := k)
      (q := 2)
      hkK
      hquot_ne_zero
      hden_ne_zero
  have hnum := two_adic_pow_sub_one_factorization_even
    (b := b) (n := K) hb_gt_one hb_odd hK_ne_zero hK_even
  have hden := two_adic_pow_sub_one_factorization_odd
    (b := b) (k := k) hb_gt_one hb_odd hk_ne_zero hk_odd
  have hplus_pos : 0 < (b + 1).factorization 2 := by
    have htwo_dvd : 2 ∣ b + 1 :=
      even_iff_two_dvd.mp (Odd.add_odd hb_odd odd_one)
    have hb1_ne_zero : b + 1 ≠ 0 := by omega
    exact Nat.prime_two.factorization_pos_of_dvd hb1_ne_zero htwo_dvd
  have hbase_le_num : (b - 1).factorization 2 ≤ (b ^ K - 1).factorization 2 := by
    omega
  rw [hquot, hden]
  omega

theorem two_adic_n0_2_odd_row_component_high_valuation
    {b K k m : Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hK_ne_zero : K ≠ 0)
    (h2K : 2 ∣ K)
    (hk_ne_zero : k ≠ 0)
    (hk_odd : Odd k)
    (hkK : k ∣ K)
    (hquot_ne_zero : ((b ^ K - 1) / (b ^ k - 1)) ≠ 0)
    (hm : m = K.factorization 2 - 1) :
    m < (((b ^ K - 1) / (b ^ k - 1)).factorization 2) := by
  have hplus := two_adic_n0_2_odd_row_component_valuation_plus_one
    (b := b) (K := K) (k := k)
    hb_gt_one hb_odd hK_ne_zero h2K hk_ne_zero hk_odd hkK hquot_ne_zero
  have hplus_pos : 0 < (b + 1).factorization 2 := by
    have htwo_dvd : 2 ∣ b + 1 :=
      even_iff_two_dvd.mp (Odd.add_odd hb_odd odd_one)
    have hb1_ne_zero : b + 1 ≠ 0 := by omega
    exact Nat.prime_two.factorization_pos_of_dvd hb1_ne_zero htwo_dvd
  have hKf_pos : 0 < K.factorization 2 :=
    Nat.prime_two.factorization_pos_of_dvd hK_ne_zero h2K
  rw [hm]
  omega

theorem two_adic_n0_2_exception_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hi0 : i0 ∈ s)
    (hi0_k : k i0 = 2)
    (hK_ne_zero : K ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ K - 1) / (b ^ k i - 1)) ≠ 0)
    (hden_ne_zero : b ^ 2 - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ K - 1) / (b ^ k i - 1))
    (hm :
      m = K.factorization 2 - 1)
    (hhigh_val :
      ∀ i, i ∈ s → i ≠ i0 → m < (T i).factorization 2)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization 2) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hW : PrimeComponentWitness L A b p 2 :=
    two_adic_n0_2_exception_supplies_PrimeComponentWitness
      (s := s)
      (i0 := i0)
      (b := b)
      (K := K)
      (m := m)
      (L := L)
      (A := A)
      (p := p)
      (k := k)
      (T := T)
      hb_gt_one hb_odd hi0 hi0_k hK_ne_zero hkK hquot_ne_zero_rows
      hden_ne_zero hT hm hhigh_val hA_eq hpcq_ne_zero hMval
  exact valuation_deficit_blocks_dvd hW.1 hW.2.1 hA hW.2.2

theorem two_adic_n0_2_exception_supplies_PrimeComponentWitness_of_odd_rows
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hi0 : i0 ∈ s)
    (hi0_k : k i0 = 2)
    (hK_ne_zero : K ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hother_odd :
      ∀ i, i ∈ s → i ≠ i0 → Odd (k i))
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ K - 1) / (b ^ k i - 1)) ≠ 0)
    (hden_ne_zero : b ^ 2 - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ K - 1) / (b ^ k i - 1))
    (hm :
      m = K.factorization 2 - 1)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization 2) :
    PrimeComponentWitness L A b p 2 := by
  refine two_adic_n0_2_exception_supplies_PrimeComponentWitness
    (s := s)
    (i0 := i0)
    (b := b)
    (K := K)
    (m := m)
    (L := L)
    (A := A)
    (p := p)
    (k := k)
    (T := T)
    hb_gt_one hb_odd hi0 hi0_k hK_ne_zero hkK hquot_ne_zero_rows
    hden_ne_zero hT hm ?hhigh_val hA_eq hpcq_ne_zero hMval
  intro i hi hne
  rw [hT i hi]
  have h2K : 2 ∣ K := by
    simpa [hi0_k] using hkK i0 hi0
  have hki_ne_zero : k i ≠ 0 :=
    Nat.pos_iff_ne_zero.mp (Odd.pos (hother_odd i hi hne))
  exact two_adic_n0_2_odd_row_component_high_valuation
    (b := b)
    (K := K)
    (k := k i)
    (m := m)
    hb_gt_one
    hb_odd
    hK_ne_zero
    h2K
    hki_ne_zero
    (hother_odd i hi hne)
    (hkK i hi)
    (hquot_ne_zero_rows i hi)
    hm

theorem two_adic_n0_2_exception_blocks_collapse_of_odd_rows
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hi0 : i0 ∈ s)
    (hi0_k : k i0 = 2)
    (hK_ne_zero : K ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hother_odd :
      ∀ i, i ∈ s → i ≠ i0 → Odd (k i))
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ K - 1) / (b ^ k i - 1)) ≠ 0)
    (hden_ne_zero : b ^ 2 - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ K - 1) / (b ^ k i - 1))
    (hm :
      m = K.factorization 2 - 1)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization 2) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hW : PrimeComponentWitness L A b p 2 :=
    two_adic_n0_2_exception_supplies_PrimeComponentWitness_of_odd_rows
      (s := s)
      (i0 := i0)
      (b := b)
      (K := K)
      (m := m)
      (L := L)
      (A := A)
      (p := p)
      (k := k)
      (T := T)
      hb_gt_one hb_odd hi0 hi0_k hK_ne_zero hkK hother_odd
      hquot_ne_zero_rows hden_ne_zero hT hm hA_eq hpcq_ne_zero hMval
  exact valuation_deficit_blocks_dvd hW.1 hW.2.1 hA hW.2.2

theorem zsigmondy_exception_blocks_collapse_of_odd_rows
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hi0 : i0 ∈ s)
    (hi0_k : k i0 = 2)
    (hK_ne_zero : K ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hother_odd :
      ∀ i, i ∈ s → i ≠ i0 → Odd (k i))
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ K - 1) / (b ^ k i - 1)) ≠ 0)
    (hden_ne_zero : b ^ 2 - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ K - 1) / (b ^ k i - 1))
    (hm :
      m = K.factorization 2 - 1)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization 2) :
    ¬ primeComponentQuotient b L p ∣ A :=
  two_adic_n0_2_exception_blocks_collapse_of_odd_rows
    (s := s)
    (i0 := i0)
    (b := b)
    (K := K)
    (m := m)
    (L := L)
    (A := A)
    (p := p)
    (k := k)
    (T := T)
    hb_gt_one hb_odd hi0 hi0_k hK_ne_zero hkK hother_odd
    hquot_ne_zero_rows hden_ne_zero hT hm hA hA_eq hpcq_ne_zero hMval

theorem zsigmondy_exception_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hb_gt_one : 1 < b)
    (hb_odd : Odd b)
    (hi0 : i0 ∈ s)
    (hi0_k : k i0 = 2)
    (hK_ne_zero : K ≠ 0)
    (hkK :
      ∀ i, i ∈ s → k i ∣ K)
    (hquot_ne_zero_rows :
      ∀ i, i ∈ s →
        ((b ^ K - 1) / (b ^ k i - 1)) ≠ 0)
    (hden_ne_zero : b ^ 2 - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ s →
        T i = (b ^ K - 1) / (b ^ k i - 1))
    (hm :
      m = K.factorization 2 - 1)
    (hhigh_val :
      ∀ i, i ∈ s → i ≠ i0 → m < (T i).factorization 2)
    (hA : A ≠ 0)
    (hA_eq :
      A = ∑ i ∈ s, T i)
    (hpcq_ne_zero :
      primeComponentQuotient b L p ≠ 0)
    (hMval :
      m < (primeComponentQuotient b L p).factorization 2) :
    ¬ primeComponentQuotient b L p ∣ A :=
  two_adic_n0_2_exception_blocks_collapse
    (s := s)
    (i0 := i0)
    (b := b)
    (K := K)
    (m := m)
    (L := L)
    (A := A)
    (p := p)
    (k := k)
    (T := T)
    hb_gt_one hb_odd hi0 hi0_k hK_ne_zero hkK hquot_ne_zero_rows
    hden_ne_zero hT hm hhigh_val hA hA_eq hpcq_ne_zero hMval

def OddComponentCanonicalCase
    (L A b p q : Nat) : Prop :=
  ∃ (ι : Type) (_ : DecidableEq ι)
      (s : Finset ι) (i0 : ι)
      (d K m : Nat)
      (k : ι → Nat) (T : ι → Nat),
    Nat.Prime q ∧
      Odd q ∧
      ∃ hcop : Nat.Coprime b q,
      d = orderOf (ZMod.unitOfCoprime b hcop) ∧
      1 < b ^ d ∧
      i0 ∈ s ∧
      K ≠ 0 ∧
      (∀ i, i ∈ s → k i ≠ 0) ∧
      (∀ i, i ∈ s → k i ∣ K) ∧
      (∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0) ∧
      (∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0) ∧
      (∀ i, i ∈ s →
        T i = (b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ∧
      m = K.factorization q - (k i0).factorization q ∧
      (∀ i, i ∈ s → i ≠ i0 →
        (k i).factorization q < (k i0).factorization q) ∧
      A = ∑ i ∈ s, T i ∧
      primeComponentQuotient b L p ≠ 0 ∧
      m < (primeComponentQuotient b L p).factorization q

def Q2ExceptionCanonicalCase
    (L A b p : Nat) : Prop :=
  ∃ (ι : Type) (_ : DecidableEq ι)
      (s : Finset ι) (i0 : ι)
      (K m : Nat)
      (k : ι → Nat) (T : ι → Nat),
    1 < b ∧
      Odd b ∧
      i0 ∈ s ∧
      k i0 = 2 ∧
      K ≠ 0 ∧
      (∀ i, i ∈ s → k i ∣ K) ∧
      (∀ i, i ∈ s → i ≠ i0 → Odd (k i)) ∧
      (∀ i, i ∈ s →
        ((b ^ K - 1) / (b ^ k i - 1)) ≠ 0) ∧
      b ^ 2 - 1 ≠ 0 ∧
      (∀ i, i ∈ s →
        T i = (b ^ K - 1) / (b ^ k i - 1)) ∧
      m = K.factorization 2 - 1 ∧
      A = ∑ i ∈ s, T i ∧
      primeComponentQuotient b L p ≠ 0 ∧
      m < (primeComponentQuotient b L p).factorization 2

def CanonicalWitnessRowCase
    (L A b p : Nat) : Prop :=
  (∃ q, OddComponentCanonicalCase L A b p q) ∨
    Q2ExceptionCanonicalCase L A b p ∨
      ∃ q, PrimeComponentWitness L A b p q

theorem odd_component_canonical_case_supplies_PrimeComponentWitness
    {L A b p q : Nat}
    (hcase : OddComponentCanonicalCase L A b p q) :
    PrimeComponentWitness L A b p q := by
  rcases hcase with
    ⟨ι, hdec, s, i0, d, K, m, k, T, hq, hq_odd, hcop,
      hd_order, hbase_gt_one, hi0, hK_ne_zero, hk_ne_zero, hkK,
      hquot_ne_zero_rows, hden_ne_zero, hT, hm, hstrict_max,
      hA_eq, hpcq_ne_zero, hMval⟩
  letI := hdec
  exact odd_component_canonical_row_supplies_PrimeComponentWitness
    (s := s)
    (i0 := i0)
    (b := b)
    (q := q)
    (d := d)
    (K := K)
    (m := m)
    (L := L)
    (A := A)
    (p := p)
    (k := k)
    (T := T)
    hq hq_odd hcop hd_order hbase_gt_one hi0 hK_ne_zero hk_ne_zero
    hkK hquot_ne_zero_rows hden_ne_zero hT hm hstrict_max hA_eq
    hpcq_ne_zero hMval

theorem q2_exception_canonical_case_supplies_PrimeComponentWitness
    {L A b p : Nat}
    (hcase : Q2ExceptionCanonicalCase L A b p) :
    PrimeComponentWitness L A b p 2 := by
  rcases hcase with
    ⟨ι, hdec, s, i0, K, m, k, T, hb_gt_one, hb_odd, hi0,
      hi0_k, hK_ne_zero, hkK, hother_odd, hquot_ne_zero_rows,
      hden_ne_zero, hT, hm, hA_eq, hpcq_ne_zero, hMval⟩
  letI := hdec
  exact two_adic_n0_2_exception_supplies_PrimeComponentWitness_of_odd_rows
    (s := s)
    (i0 := i0)
    (b := b)
    (K := K)
    (m := m)
    (L := L)
    (A := A)
    (p := p)
    (k := k)
    (T := T)
    hb_gt_one hb_odd hi0 hi0_k hK_ne_zero hkK hother_odd
    hquot_ne_zero_rows hden_ne_zero hT hm hA_eq hpcq_ne_zero hMval

theorem CanonicalWitnessRowCase.supplies_PrimeComponentWitness
    {L A b p : Nat}
    (hcase : CanonicalWitnessRowCase L A b p) :
    ∃ q, PrimeComponentWitness L A b p q := by
  rcases hcase with hodd | hq2_or_direct
  · rcases hodd with ⟨q, hcase⟩
    exact ⟨q, odd_component_canonical_case_supplies_PrimeComponentWitness hcase⟩
  · rcases hq2_or_direct with hq2 | hdirect
    · exact ⟨2, q2_exception_canonical_case_supplies_PrimeComponentWitness hq2⟩
    · exact hdirect

theorem canonical_witness_singleton_minimality_supplies_witness_existence
    {L A b : Nat}
    (hcase :
      ∀ p, Nat.Prime p → p ∣ L →
        CanonicalWitnessRowCase L A b p) :
    ∀ p, Nat.Prime p → p ∣ L →
      ∃ q, PrimeComponentWitness L A b p q := by
  intro p hp hpL
  exact CanonicalWitnessRowCase.supplies_PrimeComponentWitness
    (hcase p hp hpL)

theorem finite_period_noncollapse_from_witness_route
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (hcase :
      ∀ p, Nat.Prime p → p ∣ L →
        CanonicalWitnessRowCase L A b p) :
    orderOf (ZMod.unitOfCoprime b hcop) = L :=
  witness_existence_implies_period_noncollapse
    L A B Q b hcop hLpos hA h_ord_dvd_L hQpos hQ hB_eq hpow
    (canonical_witness_singleton_minimality_supplies_witness_existence hcase)

def FiniteCanonicalWitnessRows
    (L A b : Nat) : Prop :=
  ∃ rows : Finset Nat,
    (∀ p, Nat.Prime p → p ∣ L → p ∈ rows) ∧
      (∀ p, p ∈ rows → CanonicalWitnessRowCase L A b p)

theorem finite_certificate_rows_supply_CanonicalWitnessRowCase
    {L A b : Nat}
    (hrows : FiniteCanonicalWitnessRows L A b) :
    ∀ p, Nat.Prime p → p ∣ L →
      CanonicalWitnessRowCase L A b p := by
  intro p hp hpL
  rcases hrows with ⟨rows, hcover, hcase⟩
  exact hcase p (hcover p hp hpL)

theorem finite_period_noncollapse_from_residue_shapes
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (hrows : FiniteCanonicalWitnessRows L A b) :
    orderOf (ZMod.unitOfCoprime b hcop) = L :=
  finite_period_noncollapse_from_witness_route
    L A B Q b hcop hLpos hA h_ord_dvd_L hQpos hQ hB_eq hpow
    (finite_certificate_rows_supply_CanonicalWitnessRowCase hrows)

def GeneratedFiniteCanonicalWitnessRows
    (L A b : Nat) : Prop :=
  L ≠ 0 ∧
    ∀ p, p ∈ L.factorization.support →
      CanonicalWitnessRowCase L A b p

theorem generated_finite_certificate_rows_supply_FiniteCanonicalWitnessRows
    {L A b : Nat}
    (hrows : GeneratedFiniteCanonicalWitnessRows L A b) :
    FiniteCanonicalWitnessRows L A b := by
  rcases hrows with ⟨hL_ne_zero, hcase⟩
  refine ⟨L.factorization.support, ?cover, hcase⟩
  intro p hp hpL
  have hpos : 0 < L.factorization p :=
    hp.factorization_pos_of_dvd hL_ne_zero hpL
  exact Finsupp.mem_support_iff.mpr (Nat.ne_of_gt hpos)

theorem finite_period_noncollapse_from_generated_finite_rows
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (hrows : GeneratedFiniteCanonicalWitnessRows L A b) :
    orderOf (ZMod.unitOfCoprime b hcop) = L :=
  finite_period_noncollapse_from_residue_shapes
    L A B Q b hcop hLpos hA h_ord_dvd_L hQpos hQ hB_eq hpow
    (generated_finite_certificate_rows_supply_FiniteCanonicalWitnessRows hrows)

theorem generated_support_table_supplies_GeneratedFiniteCanonicalWitnessRows
    {L A b : Nat}
    {rows : Finset Nat}
    (hL_ne_zero : L ≠ 0)
    (hcover : ∀ p, p ∈ L.factorization.support → p ∈ rows)
    (hcase : ∀ p, p ∈ rows → CanonicalWitnessRowCase L A b p) :
    GeneratedFiniteCanonicalWitnessRows L A b := by
  refine ⟨hL_ne_zero, ?_⟩
  intro p hp
  exact hcase p (hcover p hp)

inductive EmittedGeneratedRowCase
    (L A b p : Nat) : Prop
| odd_component
    {q : Nat}
    (hodd : OddComponentCanonicalCase L A b p q) :
    EmittedGeneratedRowCase L A b p
| q2_exception
    (hq2 : Q2ExceptionCanonicalCase L A b p) :
    EmittedGeneratedRowCase L A b p
| prime_witness
    {q : Nat}
    (hwit : PrimeComponentWitness L A b p q) :
    EmittedGeneratedRowCase L A b p

theorem EmittedGeneratedRowCase.supplies_CanonicalWitnessRowCase
    {L A b p : Nat}
    (hrow : EmittedGeneratedRowCase L A b p) :
    CanonicalWitnessRowCase L A b p := by
  cases hrow with
  | odd_component hodd =>
      exact Or.inl ⟨_, hodd⟩
  | q2_exception hq2 =>
      exact Or.inr (Or.inl hq2)
  | prime_witness hwit =>
      exact Or.inr (Or.inr ⟨_, hwit⟩)

theorem emitted_generated_row_table_supplies_GeneratedFiniteCanonicalWitnessRows
    {L A b : Nat}
    {rows : Finset Nat}
    (hL_ne_zero : L ≠ 0)
    (hcover : ∀ p, p ∈ L.factorization.support → p ∈ rows)
    (hrow : ∀ p, p ∈ rows → EmittedGeneratedRowCase L A b p) :
    GeneratedFiniteCanonicalWitnessRows L A b := by
  exact generated_support_table_supplies_GeneratedFiniteCanonicalWitnessRows
    hL_ne_zero hcover
    (fun p hp =>
      EmittedGeneratedRowCase.supplies_CanonicalWitnessRowCase (hrow p hp))

structure EmittedCertificateTable
    (L A b : Nat) where
  rows : Finset Nat
  L_ne_zero : L ≠ 0
  covers_factor_support :
    ∀ p, p ∈ L.factorization.support → p ∈ rows
  row_sound :
    ∀ p, p ∈ rows → EmittedGeneratedRowCase L A b p

theorem emitted_certificate_table_supplies_generated_finite_rows
    {L A b : Nat}
    (cert : EmittedCertificateTable L A b) :
    GeneratedFiniteCanonicalWitnessRows L A b :=
  emitted_generated_row_table_supplies_GeneratedFiniteCanonicalWitnessRows
    cert.L_ne_zero cert.covers_factor_support cert.row_sound

theorem emitted_row_object_projection_or_broader_generated_table_route
    {L A b : Nat}
    {rows : Finset Nat}
    (hL_ne_zero : L ≠ 0)
    (hcover : ∀ p, p ∈ L.factorization.support → p ∈ rows)
    (hrow : ∀ p, p ∈ rows → EmittedGeneratedRowCase L A b p) :
    GeneratedFiniteCanonicalWitnessRows L A b :=
  emitted_generated_row_table_supplies_GeneratedFiniteCanonicalWitnessRows
    hL_ne_zero hcover hrow

theorem finite_period_noncollapse_from_emitted_certificate_table
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (cert : EmittedCertificateTable L A b) :
    orderOf (ZMod.unitOfCoprime b hcop) = L :=
  finite_period_noncollapse_from_generated_finite_rows
    L A B Q b hcop hLpos hA h_ord_dvd_L hQpos hQ hB_eq hpow
    (emitted_certificate_table_supplies_generated_finite_rows cert)

theorem finite_period_noncollapse_from_emitted_generated_row_table
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    {rows : Finset Nat}
    (hL_ne_zero : L ≠ 0)
    (hcover : ∀ p, p ∈ L.factorization.support → p ∈ rows)
    (hrow : ∀ p, p ∈ rows → EmittedGeneratedRowCase L A b p) :
    orderOf (ZMod.unitOfCoprime b hcop) = L :=
  finite_period_noncollapse_from_emitted_certificate_table
    L A B Q b hcop hLpos hA h_ord_dvd_L hQpos hQ hB_eq hpow
    { rows := rows
      L_ne_zero := hL_ne_zero
      covers_factor_support := hcover
      row_sound := hrow }

theorem concrete_generated_b2_F2_orderOf
    (hcop : Nat.Coprime 2 3) :
    orderOf (ZMod.unitOfCoprime 2 hcop) = 2 := by
  rw [orderOf_eq_prime_iff]
  constructor
  · apply Units.ext
    change (((ZMod.unitOfCoprime 2 hcop : (ZMod 3)ˣ) : ZMod 3) ^ 2) =
      (1 : ZMod 3)
    rw [ZMod.coe_unitOfCoprime]
    decide
  · intro h
    have hv := congrArg Units.val h
    change ((ZMod.unitOfCoprime 2 hcop : (ZMod 3)ˣ).val) =
      (1 : (ZMod 3)ˣ).val at hv
    rw [ZMod.coe_unitOfCoprime] at hv
    revert hv
    decide

theorem concrete_generated_b2_F2_factorization_support_cases
    {p : Nat}
    (hp : p ∈ (2 : Nat).factorization.support) :
    p = 2 := by
  rw [Nat.support_factorization] at hp
  exact (Nat.prime_dvd_prime_iff_eq
    (Nat.prime_of_mem_primeFactors hp)
    (by decide : Nat.Prime 2)).mp
    ((Nat.mem_primeFactors.mp hp).2.1)

theorem concrete_generated_b2_F2_odd_component_case :
    OddComponentCanonicalCase 2 1 2 2 3 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 2, 1, 0,
    (fun _ : Unit => 1), (fun _ : Unit => 1), ?_⟩
  refine ⟨(by decide : Nat.Prime 3), (by decide : Odd 3), ?_⟩
  refine ⟨(by decide : Nat.Coprime 2 3), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact (concrete_generated_b2_F2_orderOf (by decide : Nat.Coprime 2 3)).symm
  · decide
  · simp
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · simp [Nat.factorization_one]
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 2 2 = 3 := by decide
    rw [hquot]
    rw [Nat.Prime.factorization_self (by decide : Nat.Prime 3)]
    decide

theorem concrete_generated_b2_F2_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 2 1 2 2 := by
  exact Or.inl ⟨3, concrete_generated_b2_F2_odd_component_case⟩

theorem concrete_generated_finite_certificate_rows_supply_GeneratedFiniteCanonicalWitnessRows :
    GeneratedFiniteCanonicalWitnessRows 2 1 2 := by
  refine ⟨by decide, ?_⟩
  intro p hp
  have hp_eq : p = 2 := concrete_generated_b2_F2_factorization_support_cases hp
  subst p
  exact concrete_generated_b2_F2_CanonicalWitnessRowCase

theorem finite_period_noncollapse_from_concrete_generated_rows :
    orderOf (ZMod.unitOfCoprime 2 (by decide : Nat.Coprime 2 3)) = 2 := by
  let hcop : Nat.Coprime 2 3 := by decide
  exact finite_period_noncollapse_from_generated_finite_rows
    2 1 3 3 2 hcop
    (by decide)
    (by decide)
    (by rw [concrete_generated_b2_F2_orderOf hcop])
    (by decide)
    (by decide)
    (by decide)
    (by rw [concrete_generated_b2_F2_orderOf hcop]; decide)
    concrete_generated_finite_certificate_rows_supply_GeneratedFiniteCanonicalWitnessRows

theorem concrete_generated_b3_F2_q2_exception_case :
    Q2ExceptionCanonicalCase 2 1 3 2 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 2, 0,
    (fun _ : Unit => 2), (fun _ : Unit => 1), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · decide
  · decide
  · simp
  · decide
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · have hfactorK : (2 : Nat).factorization 2 = 1 := by
      rw [show (2 : Nat) = 2 ^ 1 by decide]
      exact Nat.factorization_pow_self (by decide : Nat.Prime 2)
    rw [hfactorK]
  · decide
  · decide
  · have hquot : primeComponentQuotient 3 2 2 = 4 := by decide
    rw [hquot]
    have hfactor : (4 : Nat).factorization 2 = 2 := by
      rw [show (4 : Nat) = 2 ^ 2 by decide]
      exact Nat.factorization_pow_self (by decide : Nat.Prime 2)
    rw [hfactor]
    decide

theorem concrete_generated_b3_F2_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 2 1 3 2 := by
  exact Or.inr (Or.inl concrete_generated_b3_F2_q2_exception_case)

theorem additional_generated_finite_certificate_rows_supply_GeneratedFiniteCanonicalWitnessRows :
    GeneratedFiniteCanonicalWitnessRows 2 1 3 := by
  refine generated_support_table_supplies_GeneratedFiniteCanonicalWitnessRows
    (L := 2)
    (A := 1)
    (b := 3)
    (rows := ({2} : Finset Nat))
    ?_ ?_ ?_
  · decide
  · intro p hp
    have hp_eq : p = 2 := concrete_generated_b2_F2_factorization_support_cases hp
    subst p
    simp
  · intro p hp
    have hp_eq : p = 2 := Finset.mem_singleton.mp hp
    subst p
    exact concrete_generated_b3_F2_CanonicalWitnessRowCase

theorem concrete_generated_b2_F6_factorization_support_cases
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

theorem concrete_generated_b2_F6_p2_odd_component_case :
    OddComponentCanonicalCase 6 1 2 2 3 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 2, 1, 0,
    (fun _ : Unit => 1), (fun _ : Unit => 1), ?_⟩
  refine ⟨(by decide : Nat.Prime 3), (by decide : Odd 3), ?_⟩
  refine ⟨(by decide : Nat.Coprime 2 3), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact (concrete_generated_b2_F2_orderOf (by decide : Nat.Coprime 2 3)).symm
  · decide
  · simp
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · simp [Nat.factorization_one]
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 6 2 = 9 := by decide
    rw [hquot]
    have hfactor : (9 : Nat).factorization 3 = 2 := by
      rw [show (9 : Nat) = 3 ^ 2 by decide]
      exact Nat.factorization_pow_self (by decide : Nat.Prime 3)
    rw [hfactor]
    decide

theorem concrete_generated_b2_F6_p2_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 6 1 2 2 := by
  exact Or.inl ⟨3, concrete_generated_b2_F6_p2_odd_component_case⟩

theorem concrete_generated_b2_F6_p3_orderOf
    (hcop : Nat.Coprime 2 7) :
    orderOf (ZMod.unitOfCoprime 2 hcop) = 3 := by
  rw [orderOf_eq_prime_iff]
  constructor
  · apply Units.ext
    change (((ZMod.unitOfCoprime 2 hcop : (ZMod 7)ˣ) : ZMod 7) ^ 3) =
      (1 : ZMod 7)
    rw [ZMod.coe_unitOfCoprime]
    decide
  · intro h
    have hv := congrArg Units.val h
    change ((ZMod.unitOfCoprime 2 hcop : (ZMod 7)ˣ).val) =
      (1 : (ZMod 7)ˣ).val at hv
    rw [ZMod.coe_unitOfCoprime] at hv
    revert hv
    decide

theorem concrete_generated_b2_F6_p3_odd_component_case :
    OddComponentCanonicalCase 6 1 2 3 7 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 3, 1, 0,
    (fun _ : Unit => 1), (fun _ : Unit => 1), ?_⟩
  refine ⟨(by decide : Nat.Prime 7), (by decide : Odd 7), ?_⟩
  refine ⟨(by decide : Nat.Coprime 2 7), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact (concrete_generated_b2_F6_p3_orderOf (by decide : Nat.Coprime 2 7)).symm
  · decide
  · simp
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · simp [Nat.factorization_one]
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 6 3 = 21 := by decide
    rw [hquot]
    have hfactor : (21 : Nat).factorization 7 = 1 := by
      rw [show (21 : Nat) = 7 * 3 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 7),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 7 ∣ 3),
      ]
    rw [hfactor]
    decide

theorem concrete_generated_b2_F6_p3_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 6 1 2 3 := by
  exact Or.inl ⟨7, concrete_generated_b2_F6_p3_odd_component_case⟩

theorem multi_support_generated_fixture_or_emitter_row_projection :
    GeneratedFiniteCanonicalWitnessRows 6 1 2 := by
  refine generated_support_table_supplies_GeneratedFiniteCanonicalWitnessRows
    (L := 6)
    (A := 1)
    (b := 2)
    (rows := ({2, 3} : Finset Nat))
    ?_ ?_ ?_
  · decide
  · intro p hp
    rcases concrete_generated_b2_F6_factorization_support_cases hp with rfl | rfl <;>
      simp
  · intro p hp
    simp at hp
    rcases hp with hp_eq | hp_eq
    · subst p
      exact concrete_generated_b2_F6_p2_CanonicalWitnessRowCase
    · subst p
      exact concrete_generated_b2_F6_p3_CanonicalWitnessRowCase

def emittedCertificate_b2_L6_A1 :
    EmittedCertificateTable 6 1 2 where
  rows := ({2, 3} : Finset Nat)
  L_ne_zero := by decide
  covers_factor_support := by
    intro p hp
    rcases concrete_generated_b2_F6_factorization_support_cases hp with rfl | rfl <;>
      simp
  row_sound := by
    intro p hp
    simp at hp
    rcases hp with hp_eq | hp_eq
    · subst p
      exact EmittedGeneratedRowCase.odd_component
        concrete_generated_b2_F6_p2_odd_component_case
    · subst p
      exact EmittedGeneratedRowCase.odd_component
        concrete_generated_b2_F6_p3_odd_component_case

theorem orderOf_b2_mod63_eq_6_from_emittedCertificate :
    orderOf (ZMod.unitOfCoprime 2 (by decide : Nat.Coprime 2 63)) = 6 := by
  let hcop : Nat.Coprime 2 63 := by decide
  have h_ord_dvd_L : orderOf (ZMod.unitOfCoprime 2 hcop) ∣ 6 := by
    have hpow_unit : (ZMod.unitOfCoprime 2 hcop) ^ 6 = 1 := by
      apply Units.ext
      change (((ZMod.unitOfCoprime 2 hcop : (ZMod 63)ˣ) : ZMod 63) ^ 6) =
        (1 : ZMod 63)
      rw [ZMod.coe_unitOfCoprime]
      decide
    exact (orderOf_dvd_iff_pow_eq_one).2 hpow_unit
  exact finite_period_noncollapse_from_emitted_certificate_table
    6 1 63 63 2 hcop
    (by decide)
    (by decide)
    h_ord_dvd_L
    (by decide)
    (by decide)
    (by decide)
    (Nat.one_le_pow (orderOf (ZMod.unitOfCoprime 2 hcop)) 2 (by decide))
    emittedCertificate_b2_L6_A1

theorem finite_period_noncollapse_from_multi_support_generated_rows :
    orderOf (ZMod.unitOfCoprime 2 (by decide : Nat.Coprime 2 63)) = 6 :=
  orderOf_b2_mod63_eq_6_from_emittedCertificate

theorem concrete_generated_b2_F10_factorization_support_cases
    {p : Nat}
    (hp : p ∈ (10 : Nat).factorization.support) :
    p = 2 ∨ p = 5 := by
  rw [Nat.support_factorization] at hp
  have hp_prime : Nat.Prime p := Nat.prime_of_mem_primeFactors hp
  have hp_dvd : p ∣ 10 := (Nat.mem_primeFactors.mp hp).2.1
  have hp_le : p ≤ 10 := Nat.le_of_dvd (by decide : 0 < 10) hp_dvd
  have hp_pos : 0 < p := hp_prime.pos
  interval_cases p
  · exact False.elim ((by decide : ¬ Nat.Prime 1) hp_prime)
  · exact Or.inl rfl
  · exact False.elim ((by decide : ¬ 3 ∣ 10) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 4) hp_prime)
  · exact Or.inr rfl
  · exact False.elim ((by decide : ¬ Nat.Prime 6) hp_prime)
  · exact False.elim ((by decide : ¬ 7 ∣ 10) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 8) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 9) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 10) hp_prime)

theorem concrete_generated_b2_F10_p2_odd_component_case :
    OddComponentCanonicalCase 10 1 2 2 3 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 2, 1, 0,
    (fun _ : Unit => 1), (fun _ : Unit => 1), ?_⟩
  refine ⟨(by decide : Nat.Prime 3), (by decide : Odd 3), ?_⟩
  refine ⟨(by decide : Nat.Coprime 2 3), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact (concrete_generated_b2_F2_orderOf (by decide : Nat.Coprime 2 3)).symm
  · decide
  · simp
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · simp [Nat.factorization_one]
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 10 2 = 33 := by decide
    rw [hquot]
    have hfactor : (33 : Nat).factorization 3 = 1 := by
      rw [show (33 : Nat) = 3 * 11 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 3),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 3 ∣ 11),
      ]
    rw [hfactor]
    decide

theorem concrete_generated_b2_F10_p2_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 10 1 2 2 := by
  exact Or.inl ⟨3, concrete_generated_b2_F10_p2_odd_component_case⟩

theorem concrete_generated_b2_F10_p5_orderOf
    (hcop : Nat.Coprime 2 11) :
    orderOf (ZMod.unitOfCoprime 2 hcop) = 10 := by
  rw [orderOf_eq_iff (by decide : 0 < 10)]
  constructor
  · apply Units.ext
    change (((ZMod.unitOfCoprime 2 hcop : (ZMod 11)ˣ) : ZMod 11) ^ 10) =
      (1 : ZMod 11)
    rw [ZMod.coe_unitOfCoprime]
    decide
  · intro m hm hpos
    interval_cases m <;> intro h
    all_goals
      have hv := congrArg Units.val h
      change (((ZMod.unitOfCoprime 2 hcop : (ZMod 11)ˣ) : ZMod 11) ^ _) =
        (1 : ZMod 11) at hv
      rw [ZMod.coe_unitOfCoprime] at hv
      revert hv
      decide

theorem concrete_generated_b2_F10_p5_odd_component_case :
    OddComponentCanonicalCase 10 1 2 5 11 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 10, 1, 0,
    (fun _ : Unit => 1), (fun _ : Unit => 1), ?_⟩
  refine ⟨(by decide : Nat.Prime 11), (by decide : Odd 11), ?_⟩
  refine ⟨(by decide : Nat.Coprime 2 11), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact (concrete_generated_b2_F10_p5_orderOf
      (by decide : Nat.Coprime 2 11)).symm
  · decide
  · simp
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · simp [Nat.factorization_one]
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 10 5 = 341 := by decide
    rw [hquot]
    have hfactor : (341 : Nat).factorization 11 = 1 := by
      rw [show (341 : Nat) = 11 * 31 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 11),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 11 ∣ 31),
      ]
    rw [hfactor]
    decide

theorem concrete_generated_b2_F10_p5_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 10 1 2 5 := by
  exact Or.inl ⟨11, concrete_generated_b2_F10_p5_odd_component_case⟩

def emittedCertificate_b2_L10_A1 :
    EmittedCertificateTable 10 1 2 where
  rows := ({2, 5} : Finset Nat)
  L_ne_zero := by decide
  covers_factor_support := by
    intro p hp
    rcases concrete_generated_b2_F10_factorization_support_cases hp with rfl | rfl <;>
      simp
  row_sound := by
    intro p hp
    simp at hp
    rcases hp with hp_eq | hp_eq
    · subst p
      exact EmittedGeneratedRowCase.odd_component
        concrete_generated_b2_F10_p2_odd_component_case
    · subst p
      exact EmittedGeneratedRowCase.odd_component
        concrete_generated_b2_F10_p5_odd_component_case

theorem orderOf_b2_mod1023_eq_10_from_emittedCertificate :
    orderOf (ZMod.unitOfCoprime 2 (by decide : Nat.Coprime 2 1023)) = 10 := by
  let hcop : Nat.Coprime 2 1023 := by decide
  have h_ord_dvd_L : orderOf (ZMod.unitOfCoprime 2 hcop) ∣ 10 := by
    have hpow_unit : (ZMod.unitOfCoprime 2 hcop) ^ 10 = 1 := by
      apply Units.ext
      change (((ZMod.unitOfCoprime 2 hcop : (ZMod 1023)ˣ) : ZMod 1023) ^ 10) =
        (1 : ZMod 1023)
      rw [ZMod.coe_unitOfCoprime]
      decide
    exact (orderOf_dvd_iff_pow_eq_one).2 hpow_unit
  exact finite_period_noncollapse_from_emitted_certificate_table
    10 1 1023 1023 2 hcop
    (by decide)
    (by decide)
    h_ord_dvd_L
    (by decide)
    (by decide)
    (by decide)
    (Nat.one_le_pow (orderOf (ZMod.unitOfCoprime 2 hcop)) 2 (by decide))
    emittedCertificate_b2_L10_A1

theorem concrete_generated_b2_F30_factorization_support_cases
    {p : Nat}
    (hp : p ∈ (30 : Nat).factorization.support) :
    p = 2 ∨ p = 3 ∨ p = 5 := by
  rw [Nat.support_factorization] at hp
  have hp_prime : Nat.Prime p := Nat.prime_of_mem_primeFactors hp
  have hp_dvd : p ∣ 30 := (Nat.mem_primeFactors.mp hp).2.1
  have hp_le : p ≤ 30 := Nat.le_of_dvd (by decide : 0 < 30) hp_dvd
  have hp_pos : 0 < p := hp_prime.pos
  interval_cases p
  · exact False.elim ((by decide : ¬ Nat.Prime 1) hp_prime)
  · exact Or.inl rfl
  · exact Or.inr (Or.inl rfl)
  · exact False.elim ((by decide : ¬ Nat.Prime 4) hp_prime)
  · exact Or.inr (Or.inr rfl)
  · exact False.elim ((by decide : ¬ Nat.Prime 6) hp_prime)
  · exact False.elim ((by decide : ¬ 7 ∣ 30) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 8) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 9) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 10) hp_prime)
  · exact False.elim ((by decide : ¬ 11 ∣ 30) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 12) hp_prime)
  · exact False.elim ((by decide : ¬ 13 ∣ 30) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 14) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 15) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 16) hp_prime)
  · exact False.elim ((by decide : ¬ 17 ∣ 30) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 18) hp_prime)
  · exact False.elim ((by decide : ¬ 19 ∣ 30) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 20) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 21) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 22) hp_prime)
  · exact False.elim ((by decide : ¬ 23 ∣ 30) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 24) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 25) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 26) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 27) hp_prime)
  · exact False.elim ((by decide : ¬ Nat.Prime 28) hp_prime)
  · exact False.elim ((by decide : ¬ 29 ∣ 30) hp_dvd)
  · exact False.elim ((by decide : ¬ Nat.Prime 30) hp_prime)

theorem concrete_generated_b2_F30_p2_odd_component_case :
    OddComponentCanonicalCase 30 1 2 2 3 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 2, 1, 0,
    (fun _ : Unit => 1), (fun _ : Unit => 1), ?_⟩
  refine ⟨(by decide : Nat.Prime 3), (by decide : Odd 3), ?_⟩
  refine ⟨(by decide : Nat.Coprime 2 3), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact (concrete_generated_b2_F2_orderOf (by decide : Nat.Coprime 2 3)).symm
  · decide
  · simp
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · simp [Nat.factorization_one]
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 30 2 = 32769 := by decide
    rw [hquot]
    have hfactor : (32769 : Nat).factorization 3 = 2 := by
      rw [show (32769 : Nat) = 3 ^ 2 * 3641 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      change (3 ^ 2 : Nat).factorization 3 + (3641 : Nat).factorization 3 = 2
      have hfactor_left : (3 ^ 2 : Nat).factorization 3 = 2 :=
        Nat.factorization_pow_self (by decide : Nat.Prime 3)
      have hfactor_right : (3641 : Nat).factorization 3 = 0 :=
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 3 ∣ 3641)
      rw [hfactor_left, hfactor_right]
    rw [hfactor]
    decide

theorem concrete_generated_b2_F30_p2_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 30 1 2 2 := by
  exact Or.inl ⟨3, concrete_generated_b2_F30_p2_odd_component_case⟩

theorem concrete_generated_b2_F30_p3_odd_component_case :
    OddComponentCanonicalCase 30 1 2 3 7 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 3, 1, 0,
    (fun _ : Unit => 1), (fun _ : Unit => 1), ?_⟩
  refine ⟨(by decide : Nat.Prime 7), (by decide : Odd 7), ?_⟩
  refine ⟨(by decide : Nat.Coprime 2 7), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact (concrete_generated_b2_F6_p3_orderOf (by decide : Nat.Coprime 2 7)).symm
  · decide
  · simp
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · simp [Nat.factorization_one]
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 30 3 = 1049601 := by decide
    rw [hquot]
    have hfactor : (1049601 : Nat).factorization 7 = 1 := by
      rw [show (1049601 : Nat) = 7 * 149943 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 7),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 7 ∣ 149943),
      ]
    rw [hfactor]
    decide

theorem concrete_generated_b2_F30_p3_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 30 1 2 3 := by
  exact Or.inl ⟨7, concrete_generated_b2_F30_p3_odd_component_case⟩

theorem concrete_generated_b2_F30_p5_odd_component_case :
    OddComponentCanonicalCase 30 1 2 5 11 := by
  refine ⟨Unit, inferInstance, ({() } : Finset Unit), (), 10, 1, 0,
    (fun _ : Unit => 1), (fun _ : Unit => 1), ?_⟩
  refine ⟨(by decide : Nat.Prime 11), (by decide : Odd 11), ?_⟩
  refine ⟨(by decide : Nat.Coprime 2 11), ?_⟩
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact (concrete_generated_b2_F10_p5_orderOf
      (by decide : Nat.Coprime 2 11)).symm
  · decide
  · simp
  · decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    decide
  · simp [Nat.factorization_one]
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 30 5 = 17043521 := by decide
    rw [hquot]
    have hfactor : (17043521 : Nat).factorization 11 = 1 := by
      rw [show (17043521 : Nat) = 11 * 1549411 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 11),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 11 ∣ 1549411),
      ]
    rw [hfactor]
    decide

theorem concrete_generated_b2_F30_p5_CanonicalWitnessRowCase :
    CanonicalWitnessRowCase 30 1 2 5 := by
  exact Or.inl ⟨11, concrete_generated_b2_F30_p5_odd_component_case⟩

def emittedCertificate_b2_L30_A1 :
    EmittedCertificateTable 30 1 2 where
  rows := ({2, 3, 5} : Finset Nat)
  L_ne_zero := by decide
  covers_factor_support := by
    intro p hp
    rcases concrete_generated_b2_F30_factorization_support_cases hp with rfl | rfl | rfl <;>
      simp
  row_sound := by
    intro p hp
    simp at hp
    rcases hp with hp_eq | hp_eq | hp_eq
    · subst p
      exact EmittedGeneratedRowCase.odd_component
        concrete_generated_b2_F30_p2_odd_component_case
    · subst p
      exact EmittedGeneratedRowCase.odd_component
        concrete_generated_b2_F30_p3_odd_component_case
    · subst p
      exact EmittedGeneratedRowCase.odd_component
        concrete_generated_b2_F30_p5_odd_component_case

theorem orderOf_b2_mod1073741823_eq_30_from_emittedCertificate :
    orderOf (ZMod.unitOfCoprime 2
      (by decide : Nat.Coprime 2 1073741823)) = 30 := by
  let hcop : Nat.Coprime 2 1073741823 := by decide
  have h_ord_dvd_L : orderOf (ZMod.unitOfCoprime 2 hcop) ∣ 30 := by
    have hpow_unit : (ZMod.unitOfCoprime 2 hcop) ^ 30 = 1 := by
      apply Units.ext
      change (((ZMod.unitOfCoprime 2 hcop : (ZMod 1073741823)ˣ) : ZMod 1073741823) ^ 30) =
        (1 : ZMod 1073741823)
      rw [ZMod.coe_unitOfCoprime]
      decide
    exact (orderOf_dvd_iff_pow_eq_one).2 hpow_unit
  exact finite_period_noncollapse_from_emitted_certificate_table
    30 1 1073741823 1073741823 2 hcop
    (by decide)
    (by decide)
    h_ord_dvd_L
    (by decide)
    (by decide)
    (by decide)
    (Nat.one_le_pow (orderOf (ZMod.unitOfCoprime 2 hcop)) 2 (by decide))
    emittedCertificate_b2_L30_A1

theorem local_layer_certificate_blocks_collapse
    {ι : Type*}
    {s : Finset ι}
    {q m L A b p : Nat}
    {T : ι → Nat}
    (hA : A ≠ 0)
    (cert : LocalLayerCertificate s q m T)
    (hA_eq : A = ∑ i ∈ s, T i)
    (hquot_ne_zero : primeComponentQuotient b L p ≠ 0)
    (hMval : m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hW : PrimeComponentWitness L A b p q :=
    local_layer_sum_certificate_supplies_PrimeComponentWitness
      cert hA_eq hquot_ne_zero hMval
  exact valuation_deficit_blocks_dvd hW.1 hW.2.1 hA hW.2.2

theorem residue_formula_certificate_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {b q d K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : ∀ i, i ∈ s → k i ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : ∀ i, i ∈ s → k i ∣ K)
    (hcomponent_quot_ne_zero :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0)
    (hresidue_not_dvd :
      ¬ q ∣
        ∑ i ∈ s,
          (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
            (K / q ^ (K.factorization q))) *
            (∏ j ∈ s.erase i,
              ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
                (k j / q ^ ((k j).factorization q))))
    (hT :
      ∀ i, i ∈ s →
        T i =
          q ^ m *
            (((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) /
              q ^ (K.factorization q - (k i).factorization q)))
    (hA : A ≠ 0)
    (hA_eq : A = ∑ i ∈ s, T i)
    (hquot_ne_zero : primeComponentQuotient b L p ≠ 0)
    (hMval : m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hsum_not_dvd :
      ¬ q ∣
        ∑ i ∈ s,
          ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) /
            q ^ (K.factorization q - (k i).factorization q) :=
    odd_prime_order_residue_formula_not_dvd_sum
      (b := b) (q := q) (d := d) (K := K) (k := k)
      hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero hK_ne_zero
      hkK hcomponent_quot_ne_zero hden_ne_zero hresidue_not_dvd
  have cert :
      LocalLayerCertificate s q m T :=
    LocalLayerCertificate.of_q_pow_decomposition
      (R := fun i =>
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) /
          q ^ (K.factorization q - (k i).factorization q))
      hq hT hsum_not_dvd
  exact local_layer_certificate_blocks_collapse
    (s := s) (q := q) (m := m) (L := L) (A := A) (b := b) (p := p)
    (T := T) hA cert hA_eq hquot_ne_zero hMval

theorem residue_formula_singleton_certificate_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {s : Finset ι}
    {i0 : ι}
    {b q d K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : ∀ i, i ∈ s → k i ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : ∀ i, i ∈ s → k i ∣ K)
    (hcomponent_quot_ne_zero :
      ∀ i, i ∈ s →
        ((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) ≠ 0)
    (hden_ne_zero :
      ∀ i, i ∈ s → b ^ (d * k i) - 1 ≠ 0)
    (hi0 : i0 ∈ s)
    (hresidue_unit :
      ¬ q ∣
        (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
          (K / q ^ (K.factorization q))) *
          (∏ j ∈ s.erase i0,
            ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
              (k j / q ^ ((k j).factorization q))))
    (hresidue_rest :
      ∀ i, i ∈ s → i ≠ i0 →
        q ∣
          (((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
            (K / q ^ (K.factorization q))) *
            (∏ j ∈ s.erase i,
              ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
                (k j / q ^ ((k j).factorization q))))
    (hT :
      ∀ i, i ∈ s →
        T i =
          q ^ m *
            (((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) /
              q ^ (K.factorization q - (k i).factorization q)))
    (hA : A ≠ 0)
    (hA_eq : A = ∑ i ∈ s, T i)
    (hquot_ne_zero : primeComponentQuotient b L p ≠ 0)
    (hMval : m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  exact residue_formula_certificate_blocks_collapse
    (s := s) (b := b) (q := q) (d := d) (K := K) (m := m)
    (L := L) (A := A) (p := p) (k := k) (T := T)
    hq hq_odd hcop hd_order hbase_gt_one hk_ne_zero hK_ne_zero
    hkK hcomponent_quot_ne_zero hden_ne_zero
    (residue_formula_singleton_nonzero_certificate
      (s := s)
      (i0 := i0)
      (q := q)
      (commonResidue :=
        ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
          (K / q ^ (K.factorization q)))
      (D := fun j =>
        ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
          (k j / q ^ ((k j).factorization q)))
      hi0 hresidue_unit hresidue_rest)
    hT hA hA_eq hquot_ne_zero hMval

theorem not_dvd_mul_of_prime_not_dvd
    {q a b : Nat}
    (hq : Nat.Prime q)
    (ha : ¬ q ∣ a)
    (hb : ¬ q ∣ b) :
    ¬ q ∣ a * b := by
  intro hmul
  rcases hq.dvd_mul.mp hmul with hdiv | hdiv
  · exact ha hdiv
  · exact hb hdiv

theorem residue_formula_singleton_residue_unit_not_dvd
    {b q d K : Nat}
    (hq : Nat.Prime q)
    (hbase_ne_zero : b ^ d - 1 ≠ 0)
    (hK_ne_zero : K ≠ 0) :
    ¬ q ∣
      ((b ^ d - 1) / q ^ ((b ^ d - 1).factorization q)) *
        (K / q ^ (K.factorization q)) := by
  exact not_dvd_mul_of_prime_not_dvd hq
    (normalized_factorization_unit_not_dvd
      (q := q)
      (N := b ^ d - 1)
      hq
      hbase_ne_zero)
    (normalized_factorization_unit_not_dvd
      (q := q)
      (N := K)
      hq
      hK_ne_zero)

theorem residue_formula_singleton_finset_certificate_blocks_collapse
    {ι : Type*}
    [DecidableEq ι]
    {i0 : ι}
    {b q d K m L A p : Nat}
    {k : ι → Nat}
    {T : ι → Nat}
    (hq : Nat.Prime q)
    (hq_odd : Odd q)
    (hcop : Nat.Coprime b q)
    (hd_order : d = orderOf (ZMod.unitOfCoprime b hcop))
    (hbase_gt_one : 1 < b ^ d)
    (hk_ne_zero : k i0 ≠ 0)
    (hK_ne_zero : K ≠ 0)
    (hkK : k i0 ∣ K)
    (hcomponent_quot_ne_zero :
      ((b ^ (d * K) - 1) / (b ^ (d * k i0) - 1)) ≠ 0)
    (hden_ne_zero :
      b ^ (d * k i0) - 1 ≠ 0)
    (hT :
      ∀ i, i ∈ ({i0} : Finset ι) →
        T i =
          q ^ m *
            (((b ^ (d * K) - 1) / (b ^ (d * k i) - 1)) /
              q ^ (K.factorization q - (k i).factorization q)))
    (hA : A ≠ 0)
    (hA_eq : A = ∑ i ∈ ({i0} : Finset ι), T i)
    (hquot_ne_zero : primeComponentQuotient b L p ≠ 0)
    (hMval : m < (primeComponentQuotient b L p).factorization q) :
    ¬ primeComponentQuotient b L p ∣ A := by
  have hbase_ne_zero : b ^ d - 1 ≠ 0 :=
    Nat.sub_ne_zero_of_lt hbase_gt_one
  refine residue_formula_singleton_certificate_blocks_collapse
    (s := ({i0} : Finset ι))
    (i0 := i0)
    (b := b)
    (q := q)
    (d := d)
    (K := K)
    (m := m)
    (L := L)
    (A := A)
    (p := p)
    (k := k)
    (T := T)
    hq hq_odd hcop hd_order hbase_gt_one ?hk_ne_zero_all hK_ne_zero
    ?hkK_all ?hcomponent_all ?hden_all ?hi0 ?hresidue_unit ?hresidue_rest
    hT hA hA_eq hquot_ne_zero hMval
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    exact hk_ne_zero
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    exact hkK
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    exact hcomponent_quot_ne_zero
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    exact hden_ne_zero
  · simp
  · simpa using
      residue_formula_singleton_residue_unit_not_dvd
        (b := b) (q := q) (d := d) (K := K)
        hq hbase_ne_zero hK_ne_zero
  · intro i hi hne
    rcases Finset.mem_singleton.mp hi with rfl
    exact (hne rfl).elim

theorem LocalLayerCertificate.singleton
    {α : Type*} [DecidableEq α]
    (x : α)
    (T : α → Nat)
    (q m : Nat)
    (hq : Nat.Prime q)
    (hdvd : q ^ m ∣ T x)
    (hres : ¬ q ∣ (T x / q ^ m)) :
    LocalLayerCertificate ({x} : Finset α) q m T := by
  refine ⟨hq, ?_, ?_⟩
  · intro i hi
    rcases Finset.mem_singleton.mp hi with rfl
    exact hdvd
  · simpa using hres

theorem LocalLayerCertificate.singleton_q_pow_exact
    {α : Type*} [DecidableEq α]
    (x : α)
    (T : α → Nat)
    (q m : Nat)
    (hq : Nat.Prime q)
    (hT_eq : ∃ r, T x = q ^ m * r ∧ ¬ q ∣ r) :
    LocalLayerCertificate ({x} : Finset α) q m T := by
  obtain ⟨r, hTx, hres⟩ := hT_eq
  have hq_pos : 0 < q := hq.pos
  have hq_pow_pos : 0 < q ^ m := pow_pos hq_pos m
  have hdvd : q ^ m ∣ T x := ⟨r, hTx⟩
  refine LocalLayerCertificate.singleton x T q m hq hdvd ?_
  rw [hTx, Nat.mul_div_cancel_left _ hq_pow_pos]
  exact hres

theorem b2_F2_localLayerCertificate_fixture :
    LocalLayerCertificate ({() } : Finset Unit) 3 0 (fun _ : Unit => 1) := by
  refine LocalLayerCertificate.singleton_q_pow_exact
    ()
    (fun _ : Unit => 1)
    3
    0
    (by decide)
    ?_
  exact ⟨1, by decide, by decide⟩

theorem b2_F2_PrimeComponentWitness_fixture :
    PrimeComponentWitness 2 1 2 2 3 := by
  refine local_layer_sum_certificate_supplies_PrimeComponentWitness
    b2_F2_localLayerCertificate_fixture
    ?_
    ?_
    ?_
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 2 2 = 3 := by decide
    rw [hquot]
    rw [Nat.Prime.factorization_self (by decide : Nat.Prime 3)]
    decide

theorem b2_F2_local_layer_blocks_collapse_fixture :
    ¬ primeComponentQuotient 2 2 2 ∣ 1 := by
  refine local_layer_certificate_blocks_collapse
    (A := 1)
    (L := 2)
    (b := 2)
    (p := 2)
    (q := 3)
    (m := 0)
    (s := ({() } : Finset Unit))
    (T := fun _ : Unit => 1)
    (by decide)
    b2_F2_localLayerCertificate_fixture
    ?_
    ?_
    ?_
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 2 2 = 3 := by decide
    rw [hquot]
    rw [Nat.Prime.factorization_self (by decide : Nat.Prime 3)]
    decide

theorem b2_F6_p2_localLayerCertificate_fixture :
    LocalLayerCertificate ({() } : Finset Unit) 3 0 (fun _ : Unit => 1) := by
  exact b2_F2_localLayerCertificate_fixture

theorem b2_F6_p2_PrimeComponentWitness_fixture :
    PrimeComponentWitness 6 1 2 2 3 := by
  refine local_layer_sum_certificate_supplies_PrimeComponentWitness
    b2_F6_p2_localLayerCertificate_fixture
    ?_
    ?_
    ?_
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 6 2 = 9 := by decide
    rw [hquot]
    have hfactor : (9 : Nat).factorization 3 = 2 := by
      rw [show (9 : Nat) = 3 ^ 2 by decide]
      exact Nat.factorization_pow_self (by decide : Nat.Prime 3)
    rw [hfactor]
    decide

theorem b2_F6_p2_local_layer_blocks_collapse_fixture :
    ¬ primeComponentQuotient 2 6 2 ∣ 1 := by
  refine local_layer_certificate_blocks_collapse
    (A := 1)
    (L := 6)
    (b := 2)
    (p := 2)
    (q := 3)
    (m := 0)
    (s := ({() } : Finset Unit))
    (T := fun _ : Unit => 1)
    (by decide)
    b2_F6_p2_localLayerCertificate_fixture
    ?_
    ?_
    ?_
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 6 2 = 9 := by decide
    rw [hquot]
    have hfactor : (9 : Nat).factorization 3 = 2 := by
      rw [show (9 : Nat) = 3 ^ 2 by decide]
      exact Nat.factorization_pow_self (by decide : Nat.Prime 3)
    rw [hfactor]
    decide

def b2_F3_6_p3_terms (i : Bool) : Nat :=
  if i then 1 else 9

theorem b2_F3_6_p3_multiLocalLayerCertificate_fixture :
    LocalLayerCertificate
      (Finset.univ : Finset Bool)
      7
      0
      b2_F3_6_p3_terms := by
  refine ⟨(by decide : Nat.Prime 7), ?_, ?_⟩
  · intro i _hi
    exact one_dvd (b2_F3_6_p3_terms i)
  · decide

theorem b2_F3_6_p3_PrimeComponentWitness_fixture :
    PrimeComponentWitness 6 10 2 3 7 := by
  refine local_layer_sum_certificate_supplies_PrimeComponentWitness
    b2_F3_6_p3_multiLocalLayerCertificate_fixture
    ?_
    ?_
    ?_
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 6 3 = 21 := by decide
    rw [hquot]
    have hfactor : (21 : Nat).factorization 7 = 1 := by
      rw [show (21 : Nat) = 7 * 3 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 7),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 7 ∣ 3),
      ]
    rw [hfactor]
    decide

theorem b2_F3_6_p3_local_layer_blocks_collapse_fixture :
    ¬ primeComponentQuotient 2 6 3 ∣ 10 := by
  refine local_layer_certificate_blocks_collapse
    (A := 10)
    (L := 6)
    (b := 2)
    (p := 3)
    (q := 7)
    (m := 0)
    (s := (Finset.univ : Finset Bool))
    (T := b2_F3_6_p3_terms)
    (by decide)
    b2_F3_6_p3_multiLocalLayerCertificate_fixture
    ?_
    ?_
    ?_
  · decide
  · decide
  · have hquot : primeComponentQuotient 2 6 3 = 21 := by decide
    rw [hquot]
    have hfactor : (21 : Nat).factorization 7 = 1 := by
      rw [show (21 : Nat) = 7 * 3 by decide]
      rw [Nat.factorization_mul (by decide) (by decide)]
      simp [
        Nat.Prime.factorization_self (by decide : Nat.Prime 7),
        Nat.factorization_eq_zero_of_not_dvd (by decide : ¬ 7 ∣ 3),
      ]
    rw [hfactor]
    decide

theorem local_layer_witness_family_implies_period_noncollapse
    {ι : Type*}
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (S : Nat → Finset ι)
    (T : Nat → ι → Nat)
    (m q : Nat → Nat)
    (h_local :
      ∀ p, Nat.Prime p → p ∣ L →
        LocalLayerCertificate (S p) (q p) (m p) (T p))
    (hA_eq :
      ∀ p, Nat.Prime p → p ∣ L →
        A = ∑ i ∈ S p, T p i)
    (hquot_ne_zero :
      ∀ p, Nat.Prime p → p ∣ L →
        primeComponentQuotient b L p ≠ 0)
    (hMval :
      ∀ p, Nat.Prime p → p ∣ L →
        m p < (primeComponentQuotient b L p).factorization (q p)) :
    orderOf (ZMod.unitOfCoprime b hcop) = L := by
  apply witness_existence_implies_period_noncollapse
    (L := L) (A := A) (B := B) (Q := Q) (b := b)
    hcop hLpos hA h_ord_dvd_L hQpos hQ hB_eq hpow
  intro p hp hpL
  exact ⟨q p,
    local_layer_sum_certificate_supplies_PrimeComponentWitness
      (h_local p hp hpL)
      (hA_eq p hp hpL)
      (hquot_ne_zero p hp hpL)
      (hMval p hp hpL)⟩

theorem local_layer_decomposition_family_implies_period_noncollapse
    {ι : Type*}
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (S : Nat → Finset ι)
    (T R : Nat → ι → Nat)
    (m q : Nat → Nat)
    (hq :
      ∀ p, Nat.Prime p → p ∣ L → Nat.Prime (q p))
    (hT :
      ∀ p, Nat.Prime p → p ∣ L →
        ∀ i, i ∈ S p → T p i = (q p) ^ (m p) * R p i)
    (hres :
      ∀ p, Nat.Prime p → p ∣ L →
        ¬ q p ∣ ∑ i ∈ S p, R p i)
    (hA_eq :
      ∀ p, Nat.Prime p → p ∣ L →
        A = ∑ i ∈ S p, T p i)
    (hquot_ne_zero :
      ∀ p, Nat.Prime p → p ∣ L →
        primeComponentQuotient b L p ≠ 0)
    (hMval :
      ∀ p, Nat.Prime p → p ∣ L →
        m p < (primeComponentQuotient b L p).factorization (q p)) :
    orderOf (ZMod.unitOfCoprime b hcop) = L := by
  apply witness_existence_implies_period_noncollapse
    (L := L) (A := A) (B := B) (Q := Q) (b := b)
    hcop hLpos hA h_ord_dvd_L hQpos hQ hB_eq hpow
  intro p hp hpL
  exact ⟨q p,
    local_layer_decomposition_supplies_PrimeComponentWitness
      (hq p hp hpL)
      (hT p hp hpL)
      (hres p hp hpL)
      (hA_eq p hp hpL)
      (hquot_ne_zero p hp hpL)
      (hMval p hp hpL)⟩

theorem minimal_layer_decomposition_family_implies_period_noncollapse
    {ι : Type*}
    [DecidableEq ι]
    (L A B Q b : Nat)
    (hcop : Nat.Coprime b Q)
    (hLpos : 0 < L)
    (hA : A ≠ 0)
    (h_ord_dvd_L : orderOf (ZMod.unitOfCoprime b hcop) ∣ L)
    (hQpos : 0 < Q)
    (hQ : Q = B / Nat.gcd A B)
    (hB_eq : B = b ^ L - 1)
    (hpow : 1 ≤ b ^ orderOf (ZMod.unitOfCoprime b hcop))
    (S M : Nat → Finset ι)
    (T R : Nat → ι → Nat)
    (m q : Nat → Nat)
    (hq :
      ∀ p, Nat.Prime p → p ∣ L → Nat.Prime (q p))
    (hsub :
      ∀ p, Nat.Prime p → p ∣ L → M p ⊆ S p)
    (hT :
      ∀ p, Nat.Prime p → p ∣ L →
        ∀ i, i ∈ S p → T p i = (q p) ^ (m p) * R p i)
    (hhigh :
      ∀ p, Nat.Prime p → p ∣ L →
        ∀ i, i ∈ S p → i ∉ M p → q p ∣ R p i)
    (hres_min :
      ∀ p, Nat.Prime p → p ∣ L →
        ¬ q p ∣ ∑ i ∈ M p, R p i)
    (hA_eq :
      ∀ p, Nat.Prime p → p ∣ L →
        A = ∑ i ∈ S p, T p i)
    (hquot_ne_zero :
      ∀ p, Nat.Prime p → p ∣ L →
        primeComponentQuotient b L p ≠ 0)
    (hMval :
      ∀ p, Nat.Prime p → p ∣ L →
        m p < (primeComponentQuotient b L p).factorization (q p)) :
    orderOf (ZMod.unitOfCoprime b hcop) = L := by
  apply witness_existence_implies_period_noncollapse
    (L := L) (A := A) (B := B) (Q := Q) (b := b)
    hcop hLpos hA h_ord_dvd_L hQpos hQ hB_eq hpow
  intro p hp hpL
  exact ⟨q p,
    minimal_layer_decomposition_supplies_PrimeComponentWitness
      (hq p hp hpL)
      (hsub p hp hpL)
      (hT p hp hpL)
      (hhigh p hp hpL)
      (hres_min p hp hpL)
      (hA_eq p hp hpL)
      (hquot_ne_zero p hp hpL)
      (hMval p hp hpL)⟩

end Erdos257PeriodNoncollapse
