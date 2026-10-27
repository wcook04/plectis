import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: ReplayAdmission

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def RequiredRow(s, source, o):
        return (((((((((((((((((((((((((((source) > (0)) and (((s).component) > (0))) and (((s).inputRef) > (0))) and (((s).evidenceClass) > (0))) and (((s).claim) > (0))) and (((0) <= ((s).nativeKind)) and (((s).nativeKind) <= (2)))) and (((o).component) == ((s).component))) and (((o).runnerComponent) == ((s).component))) and (((o).receiptComponent) == ((s).component))) and (((o).inputRef) == ((s).inputRef))) and (((o).evidenceClass) == ((s).evidenceClass))) and (((o).claim) == ((s).claim))) and (((o).sourceBefore) == (source))) and (((o).sourceAfter) == (source))) and (((o).inputBefore) > (0))) and (((o).inputBefore) == ((o).inputAfter))) and (((o).runnerPayload) > (0))) and (((o).runnerPayload) == ((o).receiptPayload))) and (((o).receiptDigest) > (0))) and ((o).receiptPresent)) and (((o).runnerStatus) == (1))) and (((o).receiptStatus) == (1))) and (((o).runnerVerdict) == (1))) and (((o).receiptVerdict) == (1))) and (((0) <= ((o).runnerNative)) and (((o).runnerNative) <= (2)))) and (((o).runnerNative) == ((o).receiptNative))) and (((o).runnerNative) == ((s).nativeKind))

    @staticmethod
    def RowDecision(s, source, o):
        return (((((((((((((((((((((((((((source) > (0)) and (((s).component) > (0))) and (((s).inputRef) > (0))) and (((s).evidenceClass) > (0))) and (((s).claim) > (0))) and (((0) <= ((s).nativeKind)) and (((s).nativeKind) <= (2)))) and (((o).component) == ((s).component))) and (((o).runnerComponent) == ((s).component))) and (((o).receiptComponent) == ((s).component))) and (((o).inputRef) == ((s).inputRef))) and (((o).evidenceClass) == ((s).evidenceClass))) and (((o).claim) == ((s).claim))) and (((o).sourceBefore) == (source))) and (((o).sourceAfter) == (source))) and (((o).inputBefore) > (0))) and (((o).inputBefore) == ((o).inputAfter))) and (((o).runnerPayload) > (0))) and (((o).runnerPayload) == ((o).receiptPayload))) and (((o).receiptDigest) > (0))) and ((o).receiptPresent)) and (((o).runnerStatus) == (1))) and (((o).receiptStatus) == (1))) and (((o).runnerVerdict) == (1))) and (((o).receiptVerdict) == (1))) and (((0) <= ((o).runnerNative)) and (((o).runnerNative) <= (2)))) and (((o).runnerNative) == ((o).receiptNative))) and (((o).runnerNative) == ((s).nativeKind))

    @staticmethod
    def CountSpec(specs, id_):
        d_0___accumulator_ = 0
        while True:
            with _dafny.label():
                if (len(specs)) == (0):
                    return (0) + (d_0___accumulator_)
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) + ((1 if (((specs)[0]).component) == (id_) else 0))
                    in0_ = _dafny.SeqWithoutIsStrInference((specs)[1::])
                    in1_ = id_
                    specs = in0_
                    id_ = in1_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def CountRow(rows, id_):
        d_0___accumulator_ = 0
        while True:
            with _dafny.label():
                if (len(rows)) == (0):
                    return (0) + (d_0___accumulator_)
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) + ((1 if (((rows)[0]).component) == (id_) else 0))
                    in0_ = _dafny.SeqWithoutIsStrInference((rows)[1::])
                    in1_ = id_
                    rows = in0_
                    id_ = in1_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def FindGood(rows, s, source):
        return ((len(rows)) > (0)) and ((default__.RowDecision(s, source, (rows)[0])) or (default__.FindGood(_dafny.SeqWithoutIsStrInference((rows)[1::]), s, source)))

    @staticmethod
    def FindSpec(specs, o, source):
        return ((len(specs)) > (0)) and ((default__.RowDecision((specs)[0], source, o)) or (default__.FindSpec(_dafny.SeqWithoutIsStrInference((specs)[1::]), o, source)))

    @staticmethod
    def CheckSpecs(pending, specs, rows, source):
        return ((len(pending)) == (0)) or (((((default__.CountSpec(specs, ((pending)[0]).component)) == (1)) and ((default__.CountRow(rows, ((pending)[0]).component)) == (1))) and (default__.FindGood(rows, (pending)[0], source))) and (default__.CheckSpecs(_dafny.SeqWithoutIsStrInference((pending)[1::]), specs, rows, source)))

    @staticmethod
    def CheckRows(pending, specs, source):
        return ((len(pending)) == (0)) or ((default__.FindSpec(specs, (pending)[0], source)) and (default__.CheckRows(_dafny.SeqWithoutIsStrInference((pending)[1::]), specs, source)))

    @staticmethod
    def Check(specs, source, rows):
        return (((((len(specs)) > (0)) and ((len(specs)) == (len(rows)))) and ((source) > (0))) and (default__.CheckSpecs(specs, specs, rows, source))) and (default__.CheckRows(rows, specs, source))

    @staticmethod
    def SpecsSatisfied(pending, specs, rows, source):
        def lambda0_(forall_var_0_):
            def lambda1_(exists_var_0_):
                d_1_j_: int = exists_var_0_
                return (((0) <= (d_1_j_)) and ((d_1_j_) < (len(rows)))) and (default__.RequiredRow((pending)[d_0_i_], source, (rows)[d_1_j_]))

            d_0_i_: int = forall_var_0_
            return not (((0) <= (d_0_i_)) and ((d_0_i_) < (len(pending)))) or ((((default__.CountSpec(specs, ((pending)[d_0_i_]).component)) == (1)) and ((default__.CountRow(rows, ((pending)[d_0_i_]).component)) == (1))) and (_dafny.quantifier(_dafny.IntegerRange(0, len(rows)), False, lambda1_)))

        return _dafny.quantifier(_dafny.IntegerRange(0, len(pending)), True, lambda0_)

    @staticmethod
    def RowsSatisfied(pending, specs, source):
        def lambda0_(forall_var_0_):
            def lambda1_(exists_var_0_):
                d_1_i_: int = exists_var_0_
                return (((0) <= (d_1_i_)) and ((d_1_i_) < (len(specs)))) and (default__.RequiredRow((specs)[d_1_i_], source, (pending)[d_0_j_]))

            d_0_j_: int = forall_var_0_
            return not (((0) <= (d_0_j_)) and ((d_0_j_) < (len(pending)))) or (_dafny.quantifier(_dafny.IntegerRange(0, len(specs)), False, lambda1_))

        return _dafny.quantifier(_dafny.IntegerRange(0, len(pending)), True, lambda0_)

    @staticmethod
    def Admission(specs, source, rows):
        return (((((len(specs)) > (0)) and ((len(specs)) == (len(rows)))) and ((source) > (0))) and (default__.SpecsSatisfied(specs, specs, rows, source))) and (default__.RowsSatisfied(rows, specs, source))

    @staticmethod
    def ExampleSpec():
        return Spec_Spec(1, 2, 3, 4, 0)

    @staticmethod
    def ExampleRow(sourceAfter, inputAfter, claim, receiptPayload, receiptDigest, nativeKind):
        return Observation_Observation(1, 1, 1, 2, 3, claim, 5, sourceAfter, 6, inputAfter, 7, receiptPayload, receiptDigest, 1, 1, 1, 1, nativeKind, nativeKind, True)

    @staticmethod
    def OtherRow():
        return Observation_Observation(9, 9, 9, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 1, 1, 1, 1, 0, 0, True)

    @staticmethod
    def WrongReceiptRow():
        return Observation_Observation(1, 1, 9, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 1, 1, 1, 1, 0, 0, True)

    @staticmethod
    def FailedStatusRow():
        return Observation_Observation(1, 1, 1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 0, 1, 1, 1, 0, 0, True)

    @staticmethod
    def AbsentReceiptRow():
        return Observation_Observation(1, 1, 1, 2, 3, 4, 5, 5, 6, 6, 7, 7, 8, 1, 1, 1, 1, 0, 0, False)


class Spec:
    @classmethod
    def default(cls, ):
        return lambda: Spec_Spec(int(0), int(0), int(0), int(0), int(0))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Spec(self) -> bool:
        return isinstance(self, Spec_Spec)

class Spec_Spec(Spec, NamedTuple('Spec', [('component', Any), ('inputRef', Any), ('evidenceClass', Any), ('claim', Any), ('nativeKind', Any)])):
    def __dafnystr__(self) -> str:
        return f'ReplayAdmission.Spec.Spec({_dafny.string_of(self.component)}, {_dafny.string_of(self.inputRef)}, {_dafny.string_of(self.evidenceClass)}, {_dafny.string_of(self.claim)}, {_dafny.string_of(self.nativeKind)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Spec_Spec) and self.component == __o.component and self.inputRef == __o.inputRef and self.evidenceClass == __o.evidenceClass and self.claim == __o.claim and self.nativeKind == __o.nativeKind
    def __hash__(self) -> int:
        return super().__hash__()


class Observation:
    @classmethod
    def default(cls, ):
        return lambda: Observation_Observation(int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), int(0), False)
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Observation(self) -> bool:
        return isinstance(self, Observation_Observation)

class Observation_Observation(Observation, NamedTuple('Observation', [('component', Any), ('runnerComponent', Any), ('receiptComponent', Any), ('inputRef', Any), ('evidenceClass', Any), ('claim', Any), ('sourceBefore', Any), ('sourceAfter', Any), ('inputBefore', Any), ('inputAfter', Any), ('runnerPayload', Any), ('receiptPayload', Any), ('receiptDigest', Any), ('runnerStatus', Any), ('receiptStatus', Any), ('runnerVerdict', Any), ('receiptVerdict', Any), ('runnerNative', Any), ('receiptNative', Any), ('receiptPresent', Any)])):
    def __dafnystr__(self) -> str:
        return f'ReplayAdmission.Observation.Observation({_dafny.string_of(self.component)}, {_dafny.string_of(self.runnerComponent)}, {_dafny.string_of(self.receiptComponent)}, {_dafny.string_of(self.inputRef)}, {_dafny.string_of(self.evidenceClass)}, {_dafny.string_of(self.claim)}, {_dafny.string_of(self.sourceBefore)}, {_dafny.string_of(self.sourceAfter)}, {_dafny.string_of(self.inputBefore)}, {_dafny.string_of(self.inputAfter)}, {_dafny.string_of(self.runnerPayload)}, {_dafny.string_of(self.receiptPayload)}, {_dafny.string_of(self.receiptDigest)}, {_dafny.string_of(self.runnerStatus)}, {_dafny.string_of(self.receiptStatus)}, {_dafny.string_of(self.runnerVerdict)}, {_dafny.string_of(self.receiptVerdict)}, {_dafny.string_of(self.runnerNative)}, {_dafny.string_of(self.receiptNative)}, {_dafny.string_of(self.receiptPresent)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Observation_Observation) and self.component == __o.component and self.runnerComponent == __o.runnerComponent and self.receiptComponent == __o.receiptComponent and self.inputRef == __o.inputRef and self.evidenceClass == __o.evidenceClass and self.claim == __o.claim and self.sourceBefore == __o.sourceBefore and self.sourceAfter == __o.sourceAfter and self.inputBefore == __o.inputBefore and self.inputAfter == __o.inputAfter and self.runnerPayload == __o.runnerPayload and self.receiptPayload == __o.receiptPayload and self.receiptDigest == __o.receiptDigest and self.runnerStatus == __o.runnerStatus and self.receiptStatus == __o.receiptStatus and self.runnerVerdict == __o.runnerVerdict and self.receiptVerdict == __o.receiptVerdict and self.runnerNative == __o.runnerNative and self.receiptNative == __o.receiptNative and self.receiptPresent == __o.receiptPresent
    def __hash__(self) -> int:
        return super().__hash__()

