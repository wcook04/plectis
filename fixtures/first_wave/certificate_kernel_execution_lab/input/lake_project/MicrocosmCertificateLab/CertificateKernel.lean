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

end MicrocosmCertificateLab

