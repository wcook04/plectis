import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: McpAuthority

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def CompleteCitations(c):
        return ((((((c).scope) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))) and (((c).argumentHash) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) and (((c).sourceCapsule) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) and (((c).instructionSplit) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) and (((c).coldReplay) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))

    @staticmethod
    def Allowed(c):
        return ((((((((((((((((c).declared) and (not((c).broad))) and (((c).scope) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "*"))))) and (((c).scope) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "all_tools"))))) and (((c).scope) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "workspace_admin"))))) and (((c).scope) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "account_full_access"))))) and (not((c).credential))) and (not((c).forbiddenKey))) and (not((c).untrustedInstruction))) and (not((c).live))) and (not((c).finalOnly))) and ((c).bodySafe)) and ((c).privateSafe)) and ((c).fieldsPresent)) and (default__.CompleteCitations(c))) and (((((c).effect) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "write")))) and (((c).effect) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "external_mutation"))))) or (((((((c).approval) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))) and (((c).approval) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "not_required"))))) and (((c).approval) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "missing"))))) and (((c).ledger) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) and (((c).rollback) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))))

    @staticmethod
    def QualifyingWrite(c):
        return (((((((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "write")))) and (((c).approval) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) and (((c).approval) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "not_required"))))) and (((c).approval) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "missing"))))) and (((c).ledger) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) and (((c).rollback) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))

    @staticmethod
    def FaultSpec(c, i):
        if (i) == (0):
            return not((c).declared)
        elif (i) == (1):
            return (((((c).broad) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "*"))))) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "all_tools"))))) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "workspace_admin"))))) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "account_full_access"))))
        elif (i) == (2):
            return ((c).credential) or ((c).forbiddenKey)
        elif (i) == (3):
            return (c).untrustedInstruction
        elif (i) == (4):
            return (c).live
        elif (i) == (5):
            return (c).finalOnly
        elif (i) == (6):
            return ((((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "write")))) or (((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "external_mutation"))))) and ((((((c).approval) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))) or (((c).approval) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "not_required"))))) or (((c).approval) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "missing"))))) or (((c).ledger) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))))
        elif (i) == (7):
            return ((((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "write")))) or (((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "external_mutation"))))) and (((c).rollback) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))
        elif (i) == (8):
            return (not((c).bodySafe)) or (not((c).privateSafe))
        elif (i) == (9):
            return (not((c).fieldsPresent)) or (not(default__.CompleteCitations(c)))
        elif True:
            return False

    @staticmethod
    def Faults(c):
        return _dafny.SeqWithoutIsStrInference([not((c).declared), (((((c).broad) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "*"))))) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "all_tools"))))) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "workspace_admin"))))) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "account_full_access")))), ((c).credential) or ((c).forbiddenKey), (c).untrustedInstruction, (c).live, (c).finalOnly, ((((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "write")))) or (((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "external_mutation"))))) and ((((((c).approval) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))) or (((c).approval) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "not_required"))))) or (((c).approval) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "missing"))))) or (((c).ledger) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))), ((((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "write")))) or (((c).effect) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "external_mutation"))))) and (((c).rollback) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))), (not((c).bodySafe)) or (not((c).privateSafe)), (((((not((c).fieldsPresent)) or (((c).scope) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) or (((c).argumentHash) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) or (((c).sourceCapsule) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) or (((c).instructionSplit) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))) or (((c).coldReplay) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, ""))))])

    @staticmethod
    def Accepted(c):
        return (default__.Faults(c)) == (_dafny.SeqWithoutIsStrInference([False, False, False, False, False, False, False, False, False, False]))

    @staticmethod
    def CountWrites(rows):
        d_0___accumulator_ = 0
        while True:
            with _dafny.label():
                if (len(rows)) == (0):
                    return (0) + (d_0___accumulator_)
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) + ((1 if default__.QualifyingWrite((rows)[0]) else 0))
                    in0_ = _dafny.SeqWithoutIsStrInference((rows)[1::])
                    rows = in0_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def CountUntrusted(rows):
        d_0___accumulator_ = 0
        while True:
            with _dafny.label():
                if (len(rows)) == (0):
                    return (0) + (d_0___accumulator_)
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) + ((1 if (((rows)[0]).toolClass) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result"))) else 0))
                    in0_ = _dafny.SeqWithoutIsStrInference((rows)[1::])
                    rows = in0_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def AllAccepted(rows):
        return ((len(rows)) == (0)) or ((default__.Accepted((rows)[0])) and (default__.AllAccepted(_dafny.SeqWithoutIsStrInference((rows)[1::]))))

    @staticmethod
    def Check(rows):
        return ((((len(rows)) == (3)) and ((default__.CountWrites(rows)) == (1))) and ((default__.CountUntrusted(rows)) == (1))) and (default__.AllAccepted(rows))

    @staticmethod
    def Batch(rows):
        writes: int = int(0)
        untrusted: int = int(0)
        accepted: bool = False
        d_0_i_: int
        d_0_i_ = 0
        writes = 0
        untrusted = 0
        d_1_ok_: bool
        d_1_ok_ = True
        while (d_0_i_) < (len(rows)):
            if default__.QualifyingWrite((rows)[d_0_i_]):
                writes = (writes) + (1)
            if (((rows)[d_0_i_]).toolClass) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result"))):
                untrusted = (untrusted) + (1)
            d_1_ok_ = (d_1_ok_) and (default__.Accepted((rows)[d_0_i_]))
            d_0_i_ = (d_0_i_) + (1)
        accepted = ((((len(rows)) == (3)) and ((writes) == (1))) and ((untrusted) == (1))) and (d_1_ok_)
        return writes, untrusted, accepted

    @staticmethod
    def ExactlyOneWrite(rows):
        return ((len(rows)) == (3)) and (((((default__.QualifyingWrite((rows)[0])) and (not(default__.QualifyingWrite((rows)[1])))) and (not(default__.QualifyingWrite((rows)[2])))) or (((not(default__.QualifyingWrite((rows)[0]))) and (default__.QualifyingWrite((rows)[1]))) and (not(default__.QualifyingWrite((rows)[2]))))) or (((not(default__.QualifyingWrite((rows)[0]))) and (not(default__.QualifyingWrite((rows)[1])))) and (default__.QualifyingWrite((rows)[2]))))

    @staticmethod
    def ExactlyOneUntrusted(rows):
        return ((len(rows)) == (3)) and ((((((((rows)[0]).toolClass) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result")))) and ((((rows)[1]).toolClass) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result"))))) and ((((rows)[2]).toolClass) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result"))))) or ((((((rows)[0]).toolClass) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result")))) and ((((rows)[1]).toolClass) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result"))))) and ((((rows)[2]).toolClass) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result")))))) or ((((((rows)[0]).toolClass) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result")))) and ((((rows)[1]).toolClass) != (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result"))))) and ((((rows)[2]).toolClass) == (_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "untrusted_result"))))))

    @staticmethod
    def BatchSpec(rows):
        def lambda0_(forall_var_0_):
            d_0_i_: int = forall_var_0_
            return not (((0) <= (d_0_i_)) and ((d_0_i_) < (len(rows)))) or (default__.Allowed((rows)[d_0_i_]))

        return ((((len(rows)) == (3)) and (default__.ExactlyOneWrite(rows))) and (default__.ExactlyOneUntrusted(rows))) and (_dafny.quantifier(_dafny.IntegerRange(0, len(rows)), True, lambda0_))

    @staticmethod
    def Example(scope, effect, toolClass, rollback):
        return Call_Call(True, scope, False, False, False, False, False, False, effect, _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "approval")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "ledger")), rollback, True, True, True, toolClass, _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "hash")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "source")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "split")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "cold")))


class Call:
    @classmethod
    def default(cls, ):
        return lambda: Call_Call(False, _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), False, False, False, False, False, False, _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), False, False, False, _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")), _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Call(self) -> bool:
        return isinstance(self, Call_Call)

class Call_Call(Call, NamedTuple('Call', [('declared', Any), ('scope', Any), ('broad', Any), ('credential', Any), ('forbiddenKey', Any), ('untrustedInstruction', Any), ('live', Any), ('finalOnly', Any), ('effect', Any), ('approval', Any), ('ledger', Any), ('rollback', Any), ('bodySafe', Any), ('privateSafe', Any), ('fieldsPresent', Any), ('toolClass', Any), ('argumentHash', Any), ('sourceCapsule', Any), ('instructionSplit', Any), ('coldReplay', Any)])):
    def __dafnystr__(self) -> str:
        return f'McpAuthority.Call.Call({_dafny.string_of(self.declared)}, {self.scope.VerbatimString(True)}, {_dafny.string_of(self.broad)}, {_dafny.string_of(self.credential)}, {_dafny.string_of(self.forbiddenKey)}, {_dafny.string_of(self.untrustedInstruction)}, {_dafny.string_of(self.live)}, {_dafny.string_of(self.finalOnly)}, {self.effect.VerbatimString(True)}, {self.approval.VerbatimString(True)}, {self.ledger.VerbatimString(True)}, {self.rollback.VerbatimString(True)}, {_dafny.string_of(self.bodySafe)}, {_dafny.string_of(self.privateSafe)}, {_dafny.string_of(self.fieldsPresent)}, {self.toolClass.VerbatimString(True)}, {self.argumentHash.VerbatimString(True)}, {self.sourceCapsule.VerbatimString(True)}, {self.instructionSplit.VerbatimString(True)}, {self.coldReplay.VerbatimString(True)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Call_Call) and self.declared == __o.declared and self.scope == __o.scope and self.broad == __o.broad and self.credential == __o.credential and self.forbiddenKey == __o.forbiddenKey and self.untrustedInstruction == __o.untrustedInstruction and self.live == __o.live and self.finalOnly == __o.finalOnly and self.effect == __o.effect and self.approval == __o.approval and self.ledger == __o.ledger and self.rollback == __o.rollback and self.bodySafe == __o.bodySafe and self.privateSafe == __o.privateSafe and self.fieldsPresent == __o.fieldsPresent and self.toolClass == __o.toolClass and self.argumentHash == __o.argumentHash and self.sourceCapsule == __o.sourceCapsule and self.instructionSplit == __o.instructionSplit and self.coldReplay == __o.coldReplay
    def __hash__(self) -> int:
        return super().__hash__()

