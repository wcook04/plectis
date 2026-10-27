import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: SandboxPolicy

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def AuthorizedWrite(r, a, c, t):
        return ((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "low_risk_public_fixture_mutation")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "filesystem_write"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "public_fixture_write"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "trusted_user_request"))))

    @staticmethod
    def ReviewedWrite(r, a, c, t):
        return ((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "review_required_side_effect")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "mock_database_update"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "mock_database_write"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "trusted_operator_approval_ref"))))

    @staticmethod
    def PolicySpec(r, a, c, t, code):
        return ((((((((code) == (1)) == (((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "secret_access")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "environment_secret_read"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "environment_read"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_tool_output")))))) and (((code) == (2)) == (((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "network_exfiltration")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "network_request"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "outbound_network"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_tool_output"))))))) and (((code) == (3)) == (((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "destructive_filesystem_mutation")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "filesystem_delete"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "filesystem_write"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_repo_file"))))))) and (((code) == (4)) == (((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "escape_payload_obfuscation")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "shell_command"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "shell_exec"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_tool_output"))))))) and (((code) == (5)) == (default__.AuthorizedWrite(r, a, c, t)))) and (((code) == (6)) == (default__.ReviewedWrite(r, a, c, t)))) and (((0) <= (code)) and ((code) <= (6)))

    @staticmethod
    def Decide(r, a, c, t):
        if ((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "secret_access")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "environment_secret_read"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "environment_read"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_tool_output")))):
            return 1
        elif ((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "network_exfiltration")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "network_request"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "outbound_network"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_tool_output")))):
            return 2
        elif ((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "destructive_filesystem_mutation")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "filesystem_delete"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "filesystem_write"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_repo_file")))):
            return 3
        elif ((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "escape_payload_obfuscation")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "shell_command"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "shell_exec"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_tool_output")))):
            return 4
        elif ((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "low_risk_public_fixture_mutation")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "filesystem_write"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "public_fixture_write"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "trusted_user_request")))):
            return 5
        elif ((((r) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "review_required_side_effect")))) and ((a) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "mock_database_update"))))) and ((c) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "mock_database_write"))))) and ((t) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "trusted_operator_approval_ref")))):
            return 6
        elif True:
            return 0

    @staticmethod
    def Evaluate(r, a, c, t):
        d_0_code_ = default__.Decide(r, a, c, t)
        if (d_0_code_) == (1):
            return (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "block")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "rule:no_secret_or_env_read_from_untrusted_context")))
        elif (d_0_code_) == (2):
            return (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "block")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "rule:no_live_network_from_untrusted_context")))
        elif (d_0_code_) == (3):
            return (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "block")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "rule:no_destructive_filesystem_mutation")))
        elif (d_0_code_) == (4):
            return (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "block")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "rule:no_executable_escape_payload_or_obfuscation")))
        elif (d_0_code_) == (5):
            return (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "allow")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "rule:public_fixture_write_with_diff_receipt")))
        elif (d_0_code_) == (6):
            return (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "review")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "rule:side_effect_requires_approval_and_rollback")))
        elif True:
            return (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "block")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "rule:sandbox_policy_fail_closed_unrecognized_action")))

