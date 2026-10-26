// SPDX-License-Identifier: Apache-2.0
// A decision over four normalized strings. The caller's normalization and the
// fidelity of recorded actions remain outside this theorem.
module SandboxPolicy {
  predicate AuthorizedWrite(r: string, a: string, c: string, t: string) {
    r == "low_risk_public_fixture_mutation" && a == "filesystem_write" &&
    c == "public_fixture_write" && t == "trusted_user_request"
  }
  predicate ReviewedWrite(r: string, a: string, c: string, t: string) {
    r == "review_required_side_effect" && a == "mock_database_update" &&
    c == "mock_database_write" && t == "trusted_operator_approval_ref"
  }
  // Rule code 0 is fail-closed; 1..4 are the named blocking rules; 5 is
  // public fixture write and 6 is the reviewed mock database write.
  predicate PolicySpec(r: string, a: string, c: string, t: string, code: int) {
    (code == 1 <==> r == "secret_access" && a == "environment_secret_read" && c == "environment_read" && t == "untrusted_tool_output") &&
    (code == 2 <==> r == "network_exfiltration" && a == "network_request" && c == "outbound_network" && t == "untrusted_tool_output") &&
    (code == 3 <==> r == "destructive_filesystem_mutation" && a == "filesystem_delete" && c == "filesystem_write" && t == "untrusted_repo_file") &&
    (code == 4 <==> r == "escape_payload_obfuscation" && a == "shell_command" && c == "shell_exec" && t == "untrusted_tool_output") &&
    (code == 5 <==> AuthorizedWrite(r,a,c,t)) &&
    (code == 6 <==> ReviewedWrite(r,a,c,t)) &&
    0 <= code <= 6
  }

  function Decide(r: string, a: string, c: string, t: string): int {
    if r == "secret_access" && a == "environment_secret_read" && c == "environment_read" && t == "untrusted_tool_output" then 1
    else if r == "network_exfiltration" && a == "network_request" && c == "outbound_network" && t == "untrusted_tool_output" then 2
    else if r == "destructive_filesystem_mutation" && a == "filesystem_delete" && c == "filesystem_write" && t == "untrusted_repo_file" then 3
    else if r == "escape_payload_obfuscation" && a == "shell_command" && c == "shell_exec" && t == "untrusted_tool_output" then 4
    else if r == "low_risk_public_fixture_mutation" && a == "filesystem_write" && c == "public_fixture_write" && t == "trusted_user_request" then 5
    else if r == "review_required_side_effect" && a == "mock_database_update" && c == "mock_database_write" && t == "trusted_operator_approval_ref" then 6
    else 0
  }

  lemma DecisionExact(r: string, a: string, c: string, t: string)
    ensures PolicySpec(r,a,c,t,Decide(r,a,c,t))
    ensures (Decide(r,a,c,t) == 5) <==> AuthorizedWrite(r,a,c,t)
    ensures (Decide(r,a,c,t) == 6) <==> ReviewedWrite(r,a,c,t)
    ensures !AuthorizedWrite(r,a,c,t) && !ReviewedWrite(r,a,c,t) ==> Decide(r,a,c,t) <= 4
  {}

  lemma UntrustedFixtureFailsClosed()
    ensures Decide("low_risk_public_fixture_mutation", "filesystem_write", "public_fixture_write", "untrusted_tool_output") == 0
  {}
  function Evaluate(r: string, a: string, c: string, t: string): (string, string) {
    var code := Decide(r,a,c,t);
    if code == 1 then ("block", "rule:no_secret_or_env_read_from_untrusted_context")
    else if code == 2 then ("block", "rule:no_live_network_from_untrusted_context")
    else if code == 3 then ("block", "rule:no_destructive_filesystem_mutation")
    else if code == 4 then ("block", "rule:no_executable_escape_payload_or_obfuscation")
    else if code == 5 then ("allow", "rule:public_fixture_write_with_diff_receipt")
    else if code == 6 then ("review", "rule:side_effect_requires_approval_and_rollback")
    else ("block", "rule:sandbox_policy_fail_closed_unrecognized_action")
  }

  lemma ReturnedVerdictExact(r: string, a: string, c: string, t: string)
    ensures (Evaluate(r,a,c,t).0 == "allow") <==> AuthorizedWrite(r,a,c,t)
    ensures (Evaluate(r,a,c,t).0 == "review") <==> ReviewedWrite(r,a,c,t)
    ensures !AuthorizedWrite(r,a,c,t) && !ReviewedWrite(r,a,c,t) ==> Evaluate(r,a,c,t).0 == "block"
    ensures AuthorizedWrite(r,a,c,t) ==> Evaluate(r,a,c,t).1 == "rule:public_fixture_write_with_diff_receipt"
    ensures ReviewedWrite(r,a,c,t) ==> Evaluate(r,a,c,t).1 == "rule:side_effect_requires_approval_and_rollback"
  { DecisionExact(r,a,c,t); }

  // The specification relates normalized action fields to the exact externally
  // visible verdict and rule text, independently of the executable branch order.
  ghost predicate OutputSpec(r: string, a: string, c: string, t: string, v: string, rule: string) {
    exists code: int :: PolicySpec(r,a,c,t,code) && (
      (code == 0 && v == "block" && rule == "rule:sandbox_policy_fail_closed_unrecognized_action") ||
      (code == 1 && v == "block" && rule == "rule:no_secret_or_env_read_from_untrusted_context") ||
      (code == 2 && v == "block" && rule == "rule:no_live_network_from_untrusted_context") ||
      (code == 3 && v == "block" && rule == "rule:no_destructive_filesystem_mutation") ||
      (code == 4 && v == "block" && rule == "rule:no_executable_escape_payload_or_obfuscation") ||
      (code == 5 && v == "allow" && rule == "rule:public_fixture_write_with_diff_receipt") ||
      (code == 6 && v == "review" && rule == "rule:side_effect_requires_approval_and_rollback"))
  }
  lemma FullOutputExact(r: string, a: string, c: string, t: string)
    ensures OutputSpec(r,a,c,t,Evaluate(r,a,c,t).0,Evaluate(r,a,c,t).1)
  { DecisionExact(r,a,c,t); }
}
