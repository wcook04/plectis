import MicrocosmCertificateLab.CertificateKernel

namespace MicrocosmCertificateLab

def cert_2_3_5 : NatSumCertificate := { left := 2, right := 3, total := 5 }
def cert_4_7_11 : NatSumCertificate := { left := 4, right := 7, total := 11 }
def cert_8_13_21 : NatSumCertificate := { left := 8, right := 13, total := 21 }
def bad_cert_2_3_6 : NatSumCertificate := { left := 2, right := 3, total := 6 }

theorem cert_2_3_5_valid : validateNatSumCertificate cert_2_3_5 = true := by
  native_decide

theorem cert_4_7_11_valid : validateNatSumCertificate cert_4_7_11 = true := by
  native_decide

theorem cert_8_13_21_valid : validateNatSumCertificate cert_8_13_21 = true := by
  native_decide

end MicrocosmCertificateLab

