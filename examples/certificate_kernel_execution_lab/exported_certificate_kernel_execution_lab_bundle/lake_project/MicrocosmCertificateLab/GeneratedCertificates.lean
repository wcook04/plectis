import MicrocosmCertificateLab.CertificateKernel

namespace MicrocosmCertificateLab

def cert_2_3_5 : NatSumCertificate := { left := 2, right := 3, total := 5 }
def cert_4_7_11 : NatSumCertificate := { left := 4, right := 7, total := 11 }
def cert_8_13_21 : NatSumCertificate := { left := 8, right := 13, total := 21 }
def bad_cert_2_3_6 : NatSumCertificate := { left := 2, right := 3, total := 6 }

def order_cert_2_3_mod5 : BoundedOrderCertificate :=
  { base := 2, period := 3, modulus := 5, witness := 0 }

def order_cert_3_4_mod5 : BoundedOrderCertificate :=
  { base := 3, period := 4, modulus := 5, witness := 2 }

def bad_order_cert_4_2_mod5 : BoundedOrderCertificate :=
  { base := 4, period := 2, modulus := 5, witness := 3 }

theorem cert_2_3_5_valid : validateNatSumCertificate cert_2_3_5 = true := by
  native_decide

theorem cert_4_7_11_valid : validateNatSumCertificate cert_4_7_11 = true := by
  native_decide

theorem cert_8_13_21_valid : validateNatSumCertificate cert_8_13_21 = true := by
  native_decide

theorem order_cert_2_3_mod5_valid :
    validateBoundedOrderCertificate order_cert_2_3_mod5 = true := by
  native_decide

theorem order_cert_3_4_mod5_valid :
    validateBoundedOrderCertificate order_cert_3_4_mod5 = true := by
  native_decide

end MicrocosmCertificateLab
