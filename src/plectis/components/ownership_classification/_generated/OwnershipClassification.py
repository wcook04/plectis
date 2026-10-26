import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: OwnershipClassification

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def Priority(state):
        if (state) == (Freshness_Live()):
            return 3
        elif (state) == (Freshness_Unknown()):
            return 2
        elif True:
            return 1

    @staticmethod
    def SelectedPrefix(claims, path, n, owner):
        if (owner) == (-1):
            def lambda0_(forall_var_0_):
                d_0_j_: int = forall_var_0_
                return not (((0) <= (d_0_j_)) and ((d_0_j_) < (n))) or ((((claims)[d_0_j_]).path) != (path))

            return _dafny.quantifier(_dafny.IntegerRange(0, n), True, lambda0_)
        elif True:
            def lambda1_(forall_var_1_):
                d_1_j_: int = forall_var_1_
                return not ((((0) <= (d_1_j_)) and ((d_1_j_) < (n))) and ((((claims)[d_1_j_]).path) == (path))) or ((default__.Priority(((claims)[d_1_j_]).freshness)) <= (default__.Priority(((claims)[owner]).freshness)))

            def lambda2_(forall_var_2_):
                d_2_j_: int = forall_var_2_
                return not ((((0) <= (d_2_j_)) and ((d_2_j_) < (owner))) and ((((claims)[d_2_j_]).path) == (path))) or ((default__.Priority(((claims)[d_2_j_]).freshness)) < (default__.Priority(((claims)[owner]).freshness)))

            return (((((0) <= (owner)) and ((owner) < (n))) and ((((claims)[owner]).path) == (path))) and (_dafny.quantifier(_dafny.IntegerRange(0, n), True, lambda1_))) and (_dafny.quantifier(_dafny.IntegerRange(0, owner), True, lambda2_))

    @staticmethod
    def HasLive(claims, path):
        def lambda0_(exists_var_0_):
            d_0_j_: int = exists_var_0_
            return ((((0) <= (d_0_j_)) and ((d_0_j_) < (len(claims)))) and ((((claims)[d_0_j_]).path) == (path))) and ((((claims)[d_0_j_]).freshness) == (Freshness_Live()))

        return _dafny.quantifier(_dafny.IntegerRange(0, len(claims)), False, lambda0_)

    @staticmethod
    def RowSpec(p, claims, row):
        return ((not((p).generated)) and ((row) == (Row_Row(-1, 0)))) or ((((p).generated) and (default__.SelectedPrefix(claims, (p).id_, len(claims), (row).ownerIndex))) and (((((row).ownerIndex) == (-1)) and (((row).kind) == (1))) or ((((0) <= ((row).ownerIndex)) and (((row).ownerIndex) < (len(claims)))) and (((((((claims)[(row).ownerIndex]).freshness) == (Freshness_Live())) and (((row).kind) == (2))) or (((((claims)[(row).ownerIndex]).freshness) == (Freshness_Unknown())) and (((row).kind) == (5)))) or (((((claims)[(row).ownerIndex]).freshness) == (Freshness_Stale())) and (((row).kind) == (3)))))))

    @staticmethod
    def ClassificationSpec(rows, c):
        def lambda0_(exists_var_0_):
            d_1_i_: int = exists_var_0_
            return (((0) <= (d_1_i_)) and ((d_1_i_) < (len(rows)))) and ((((rows)[d_1_i_]).kind) == (2))

        d_0_live_ = _dafny.quantifier(_dafny.IntegerRange(0, len(rows)), False, lambda0_)
        def lambda1_(exists_var_1_):
            d_3_i_: int = exists_var_1_
            return (((0) <= (d_3_i_)) and ((d_3_i_) < (len(rows)))) and ((((rows)[d_3_i_]).kind) == (5))

        d_2_unknown_ = _dafny.quantifier(_dafny.IntegerRange(0, len(rows)), False, lambda1_)
        def lambda2_(exists_var_2_):
            d_5_i_: int = exists_var_2_
            return (((0) <= (d_5_i_)) and ((d_5_i_) < (len(rows)))) and ((((rows)[d_5_i_]).kind) == (3))

        d_4_stale_ = _dafny.quantifier(_dafny.IntegerRange(0, len(rows)), False, lambda2_)
        def lambda3_(exists_var_3_):
            d_7_i_: int = exists_var_3_
            return (((0) <= (d_7_i_)) and ((d_7_i_) < (len(rows)))) and ((((rows)[d_7_i_]).kind) == (1))

        d_6_unowned_ = _dafny.quantifier(_dafny.IntegerRange(0, len(rows)), False, lambda3_)
        return ((((((d_0_live_) and ((c) == (2))) or (((not(d_0_live_)) and (d_2_unknown_)) and ((c) == (5)))) or ((((not(d_0_live_)) and (not(d_2_unknown_))) and (d_4_stale_)) and ((c) == (3)))) or (((((not(d_0_live_)) and (not(d_2_unknown_))) and (not(d_4_stale_))) and (d_6_unowned_)) and ((c) == (1)))) or ((((((not(d_0_live_)) and (not(d_2_unknown_))) and (not(d_4_stale_))) and (not(d_6_unowned_))) and ((len(rows)) > (0))) and ((c) == (4)))) or (((len(rows)) == (0)) and ((c) == (0)))

    @staticmethod
    def ActionSpec(c, action):
        return (((((((c) == (2)) and ((action) == (11))) or (((c) == (5)) and ((action) == (16)))) or (((c) == (3)) and ((action) == (12)))) or (((c) == (1)) and ((action) == (13)))) or (((c) == (4)) and ((action) == (14)))) or (((c) == (0)) and ((action) == (15)))

    @staticmethod
    def FindOwner(claims, path):
        owner: int = int(0)
        owner = -1
        d_0_i_: int
        d_0_i_ = 0
        while (d_0_i_) < (len(claims)):
            if (((claims)[d_0_i_]).path) == (path):
                if (((claims)[d_0_i_]).freshness) == (Freshness_Live()):
                    owner = d_0_i_
                    return owner
                if ((owner) < (0)) or ((default__.Priority(((claims)[d_0_i_]).freshness)) > (default__.Priority(((claims)[owner]).freshness))):
                    owner = d_0_i_
            d_0_i_ = (d_0_i_) + (1)
        return owner

    @staticmethod
    def Compute(paths, claims):
        rows: _dafny.Seq = _dafny.Seq({})
        classification: int = int(0)
        action: int = int(0)
        rows = _dafny.SeqWithoutIsStrInference([])
        d_0_live_: bool
        d_1_unknown_: bool
        d_2_stale_: bool
        d_3_unowned_: bool
        rhs0_ = False
        rhs1_ = False
        rhs2_ = False
        rhs3_ = False
        d_0_live_ = rhs0_
        d_1_unknown_ = rhs1_
        d_2_stale_ = rhs2_
        d_3_unowned_ = rhs3_
        d_4_i_: int
        d_4_i_ = 0
        while (d_4_i_) < (len(paths)):
            d_5_row_: Row
            d_5_row_ = Row_Row(-1, 0)
            if ((paths)[d_4_i_]).generated:
                d_6_owner_: int
                out0_: int
                out0_ = default__.FindOwner(claims, ((paths)[d_4_i_]).id_)
                d_6_owner_ = out0_
                if (d_6_owner_) < (0):
                    d_5_row_ = Row_Row(-1, 1)
                elif (((claims)[d_6_owner_]).freshness) == (Freshness_Live()):
                    d_5_row_ = Row_Row(d_6_owner_, 2)
                elif (((claims)[d_6_owner_]).freshness) == (Freshness_Unknown()):
                    d_5_row_ = Row_Row(d_6_owner_, 5)
                elif True:
                    d_5_row_ = Row_Row(d_6_owner_, 3)
            rows = (rows) + (_dafny.SeqWithoutIsStrInference([d_5_row_]))
            d_0_live_ = (d_0_live_) or (((d_5_row_).kind) == (2))
            d_1_unknown_ = (d_1_unknown_) or (((d_5_row_).kind) == (5))
            d_2_stale_ = (d_2_stale_) or (((d_5_row_).kind) == (3))
            d_3_unowned_ = (d_3_unowned_) or (((d_5_row_).kind) == (1))
            d_4_i_ = (d_4_i_) + (1)
        if d_0_live_:
            classification = 2
        elif d_1_unknown_:
            classification = 5
        elif d_2_stale_:
            classification = 3
        elif d_3_unowned_:
            classification = 1
        elif (len(rows)) > (0):
            classification = 4
        elif True:
            classification = 0
        if (classification) == (2):
            action = 11
        elif (classification) == (5):
            action = 16
        elif (classification) == (3):
            action = 12
        elif (classification) == (1):
            action = 13
        elif (classification) == (4):
            action = 14
        elif True:
            action = 15
        return rows, classification, action


class Freshness:
    @_dafny.classproperty
    def AllSingletonConstructors(cls):
        return [Freshness_Stale(), Freshness_Unknown(), Freshness_Live()]
    @classmethod
    def default(cls, ):
        return lambda: Freshness_Stale()
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Stale(self) -> bool:
        return isinstance(self, Freshness_Stale)
    @property
    def is_Unknown(self) -> bool:
        return isinstance(self, Freshness_Unknown)
    @property
    def is_Live(self) -> bool:
        return isinstance(self, Freshness_Live)

class Freshness_Stale(Freshness, NamedTuple('Stale', [])):
    def __dafnystr__(self) -> str:
        return f'OwnershipClassification.Freshness.Stale'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Freshness_Stale)
    def __hash__(self) -> int:
        return super().__hash__()

class Freshness_Unknown(Freshness, NamedTuple('Unknown', [])):
    def __dafnystr__(self) -> str:
        return f'OwnershipClassification.Freshness.Unknown'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Freshness_Unknown)
    def __hash__(self) -> int:
        return super().__hash__()

class Freshness_Live(Freshness, NamedTuple('Live', [])):
    def __dafnystr__(self) -> str:
        return f'OwnershipClassification.Freshness.Live'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Freshness_Live)
    def __hash__(self) -> int:
        return super().__hash__()


class Path:
    @classmethod
    def default(cls, ):
        return lambda: Path_Path(int(0), False)
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Path(self) -> bool:
        return isinstance(self, Path_Path)

class Path_Path(Path, NamedTuple('Path', [('id_', Any), ('generated', Any)])):
    def __dafnystr__(self) -> str:
        return f'OwnershipClassification.Path.Path({_dafny.string_of(self.id_)}, {_dafny.string_of(self.generated)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Path_Path) and self.id_ == __o.id_ and self.generated == __o.generated
    def __hash__(self) -> int:
        return super().__hash__()


class Claim:
    @classmethod
    def default(cls, ):
        return lambda: Claim_Claim(int(0), Freshness.default()())
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Claim(self) -> bool:
        return isinstance(self, Claim_Claim)

class Claim_Claim(Claim, NamedTuple('Claim', [('path', Any), ('freshness', Any)])):
    def __dafnystr__(self) -> str:
        return f'OwnershipClassification.Claim.Claim({_dafny.string_of(self.path)}, {_dafny.string_of(self.freshness)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Claim_Claim) and self.path == __o.path and self.freshness == __o.freshness
    def __hash__(self) -> int:
        return super().__hash__()


class Row:
    @classmethod
    def default(cls, ):
        return lambda: Row_Row(int(0), int(0))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Row(self) -> bool:
        return isinstance(self, Row_Row)

class Row_Row(Row, NamedTuple('Row', [('ownerIndex', Any), ('kind', Any)])):
    def __dafnystr__(self) -> str:
        return f'OwnershipClassification.Row.Row({_dafny.string_of(self.ownerIndex)}, {_dafny.string_of(self.kind)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Row_Row) and self.ownerIndex == __o.ownerIndex and self.kind == __o.kind
    def __hash__(self) -> int:
        return super().__hash__()

