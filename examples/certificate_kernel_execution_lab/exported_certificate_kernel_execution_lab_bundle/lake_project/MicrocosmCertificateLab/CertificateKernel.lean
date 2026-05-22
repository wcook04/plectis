namespace MicrocosmCertificateLab

structure NatSumCertificate where
  left : Nat
  right : Nat
  total : Nat
deriving Repr, DecidableEq

def validateNatSumCertificate (cert : NatSumCertificate) : Bool :=
  cert.left + cert.right == cert.total

def certificateRowShape (cert : NatSumCertificate) : Nat :=
  cert.left + cert.right + cert.total

structure BoundedOrderCertificate where
  base : Nat
  period : Nat
  modulus : Nat
  witness : Nat
deriving Repr, DecidableEq

def validateBoundedOrderCertificate (cert : BoundedOrderCertificate) : Bool :=
  decide (cert.period > 0) &&
    decide (cert.modulus > 0) &&
    decide (cert.base < cert.modulus) &&
    ((cert.base + cert.period) % cert.modulus == cert.witness)

def orderCertificateShape (cert : BoundedOrderCertificate) : Nat :=
  cert.base + cert.period + cert.modulus + cert.witness

end MicrocosmCertificateLab
