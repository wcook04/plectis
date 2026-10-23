import sys
from typing import Callable, Any, TypeVar, NamedTuple
from math import floor
from itertools import count

import module_ as module_
import _dafny as _dafny
import System_ as System_

# Module: Release

class default__:
    def  __init__(self):
        pass

    @staticmethod
    def ValueType(v):
        if (v).is_Text:
            return Ty_TextTy()
        elif True:
            return Ty_FlagTy()

    @staticmethod
    def ExprType(e, types):
        source0_ = e
        if True:
            if source0_.is_Literal:
                d_0_v_ = source0_.value
                return default__.ValueType(d_0_v_)
        if True:
            if source0_.is_Input:
                d_1_i_ = source0_.slot
                if ((0) <= (d_1_i_)) and ((d_1_i_) < (len(types))):
                    return (types)[d_1_i_]
                elif True:
                    return Ty_TextTy()
        if True:
            if source0_.is_Concat:
                d_2_a_ = source0_.left
                d_3_b_ = source0_.right
                return Ty_TextTy()
        if True:
            d_4_a_ = source0_.left
            d_5_b_ = source0_.right
            return Ty_FlagTy()

    @staticmethod
    def WellTypedExpr(e, types):
        source0_ = e
        if True:
            if source0_.is_Literal:
                d_0_v_ = source0_.value
                return True
        if True:
            if source0_.is_Input:
                d_1_i_ = source0_.slot
                return ((0) <= (d_1_i_)) and ((d_1_i_) < (len(types)))
        if True:
            if source0_.is_Concat:
                d_2_a_ = source0_.left
                d_3_b_ = source0_.right
                return (((default__.WellTypedExpr(d_2_a_, types)) and (default__.WellTypedExpr(d_3_b_, types))) and ((default__.ExprType(d_2_a_, types)) == (Ty_TextTy()))) and ((default__.ExprType(d_3_b_, types)) == (Ty_TextTy()))
        if True:
            d_4_a_ = source0_.left
            d_5_b_ = source0_.right
            return ((default__.WellTypedExpr(d_4_a_, types)) and (default__.WellTypedExpr(d_5_b_, types))) and ((default__.ExprType(d_4_a_, types)) == (default__.ExprType(d_5_b_, types)))

    @staticmethod
    def Sensitive(e, high):
        source0_ = e
        if True:
            if source0_.is_Literal:
                d_0_v_ = source0_.value
                return False
        if True:
            if source0_.is_Input:
                d_1_i_ = source0_.slot
                return (not(((0) <= (d_1_i_)) and ((d_1_i_) < (len(high))))) or ((high)[d_1_i_])
        if True:
            if source0_.is_Concat:
                d_2_a_ = source0_.left
                d_3_b_ = source0_.right
                return (default__.Sensitive(d_2_a_, high)) or (default__.Sensitive(d_3_b_, high))
        if True:
            d_4_a_ = source0_.left
            d_5_b_ = source0_.right
            return (default__.Sensitive(d_4_a_, high)) or (default__.Sensitive(d_5_b_, high))

    @staticmethod
    def ValidEnvironment(types, values):
        def lambda0_(forall_var_0_):
            d_0_i_: int = forall_var_0_
            return not (((0) <= (d_0_i_)) and ((d_0_i_) < (len(types)))) or ((default__.ValueType((values)[d_0_i_])) == ((types)[d_0_i_]))

        return ((len(types)) == (len(values))) and (_dafny.quantifier(_dafny.IntegerRange(0, len(types)), True, lambda0_))

    @staticmethod
    def LowEquivalent(high, left, right):
        def lambda0_(forall_var_0_):
            d_0_i_: int = forall_var_0_
            return not ((((0) <= (d_0_i_)) and ((d_0_i_) < (len(high)))) and (not((high)[d_0_i_]))) or (((left)[d_0_i_]) == ((right)[d_0_i_]))

        return (((len(left)) == (len(high))) and ((len(right)) == (len(high)))) and (_dafny.quantifier(_dafny.IntegerRange(0, len(high)), True, lambda0_))

    @staticmethod
    def Eval(e, values):
        source0_ = e
        if True:
            if source0_.is_Literal:
                d_0_v_ = source0_.value
                return d_0_v_
        if True:
            if source0_.is_Input:
                d_1_i_ = source0_.slot
                if ((0) <= (d_1_i_)) and ((d_1_i_) < (len(values))):
                    return (values)[d_1_i_]
                elif True:
                    return Value_Text(_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))
        if True:
            if source0_.is_Concat:
                d_2_a_ = source0_.left
                d_3_b_ = source0_.right
                d_4_av_ = default__.Eval(d_2_a_, values)
                d_5_bv_ = default__.Eval(d_3_b_, values)
                if ((d_4_av_).is_Text) and ((d_5_bv_).is_Text):
                    return Value_Text(((d_4_av_).text) + ((d_5_bv_).text))
                elif True:
                    return Value_Text(_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))
        if True:
            d_6_a_ = source0_.left
            d_7_b_ = source0_.right
            return Value_Flag((default__.Eval(d_6_a_, values)) == (default__.Eval(d_7_b_, values)))

    @staticmethod
    def Checked(c, types, high, pc):
        def lambda0_():
            source0_ = c
            if True:
                if source0_.is_Skip:
                    return True
            if True:
                if source0_.is_Emit:
                    d_0_isPublic_ = source0_.public
                    d_1_e_ = source0_.value
                    return ((default__.WellTypedExpr(d_1_e_, types)) and ((default__.ExprType(d_1_e_, types)) == (Ty_TextTy()))) and ((not(d_0_isPublic_)) or ((not(pc)) and (not(default__.Sensitive(d_1_e_, high)))))
            if True:
                if source0_.is_Then:
                    d_2_a_ = source0_.first
                    d_3_b_ = source0_.second
                    return (default__.Checked(d_2_a_, types, high, pc)) and (default__.Checked(d_3_b_, types, high, pc))
            if True:
                d_4_e_ = source0_.condition
                d_5_a_ = source0_.yes
                d_6_b_ = source0_.no
                return (((default__.WellTypedExpr(d_4_e_, types)) and ((default__.ExprType(d_4_e_, types)) == (Ty_FlagTy()))) and (default__.Checked(d_5_a_, types, high, (pc) or (default__.Sensitive(d_4_e_, high))))) and (default__.Checked(d_6_b_, types, high, (pc) or (default__.Sensitive(d_4_e_, high))))

        return ((len(types)) == (len(high))) and (lambda0_())

    @staticmethod
    def Run(c, values):
        source0_ = c
        if True:
            if source0_.is_Skip:
                return _dafny.SeqWithoutIsStrInference([])
        if True:
            if source0_.is_Emit:
                d_0_isPublic_ = source0_.public
                d_1_e_ = source0_.value
                d_2_v_ = default__.Eval(d_1_e_, values)
                if (d_0_isPublic_) and ((d_2_v_).is_Text):
                    return _dafny.SeqWithoutIsStrInference([(d_2_v_).text])
                elif True:
                    return _dafny.SeqWithoutIsStrInference([])
        if True:
            if source0_.is_Then:
                d_3_a_ = source0_.first
                d_4_b_ = source0_.second
                return (default__.Run(d_3_a_, values)) + (default__.Run(d_4_b_, values))
        if True:
            d_5_e_ = source0_.condition
            d_6_a_ = source0_.yes
            d_7_b_ = source0_.no
            d_8_v_ = default__.Eval(d_5_e_, values)
            if ((d_8_v_).is_Flag) and ((d_8_v_).flag):
                return default__.Run(d_6_a_, values)
            elif True:
                return default__.Run(d_7_b_, values)

    @staticmethod
    def RunAll(c, values):
        source0_ = c
        if True:
            if source0_.is_Skip:
                return _dafny.SeqWithoutIsStrInference([])
        if True:
            if source0_.is_Emit:
                d_0_isPublic_ = source0_.public
                d_1_e_ = source0_.value
                d_2_v_ = default__.Eval(d_1_e_, values)
                if (d_2_v_).is_Text:
                    return _dafny.SeqWithoutIsStrInference([Event_Emission(d_0_isPublic_, (d_2_v_).text)])
                elif True:
                    return _dafny.SeqWithoutIsStrInference([])
        if True:
            if source0_.is_Then:
                d_3_a_ = source0_.first
                d_4_b_ = source0_.second
                return (default__.RunAll(d_3_a_, values)) + (default__.RunAll(d_4_b_, values))
        if True:
            d_5_e_ = source0_.condition
            d_6_a_ = source0_.yes
            d_7_b_ = source0_.no
            d_8_v_ = default__.Eval(d_5_e_, values)
            if ((d_8_v_).is_Flag) and ((d_8_v_).flag):
                return default__.RunAll(d_6_a_, values)
            elif True:
                return default__.RunAll(d_7_b_, values)

    @staticmethod
    def PublicProjection(events):
        d_0___accumulator_ = _dafny.SeqWithoutIsStrInference([])
        while True:
            with _dafny.label():
                if (len(events)) == (0):
                    return (d_0___accumulator_) + (_dafny.SeqWithoutIsStrInference([]))
                elif True:
                    d_0___accumulator_ = (d_0___accumulator_) + ((_dafny.SeqWithoutIsStrInference([((events)[0]).text]) if ((events)[0]).isPublic else _dafny.SeqWithoutIsStrInference([])))
                    in0_ = _dafny.SeqWithoutIsStrInference((events)[1::])
                    events = in0_
                    raise _dafny.TailCall()
                break

    @staticmethod
    def PublicSlice(c, high):
        source0_ = c
        if True:
            if source0_.is_Skip:
                return Cmd_Skip()
        if True:
            if source0_.is_Emit:
                d_0_isPublic_ = source0_.public
                d_1_e_ = source0_.value
                if d_0_isPublic_:
                    return Cmd_Emit(True, d_1_e_)
                elif True:
                    return Cmd_Skip()
        if True:
            if source0_.is_Then:
                d_2_a_ = source0_.first
                d_3_b_ = source0_.second
                return Cmd_Then(default__.PublicSlice(d_2_a_, high), default__.PublicSlice(d_3_b_, high))
        if True:
            d_4_e_ = source0_.condition
            d_5_a_ = source0_.yes
            d_6_b_ = source0_.no
            if default__.Sensitive(d_4_e_, high):
                return Cmd_Skip()
            elif True:
                return Cmd_Branch(d_4_e_, default__.PublicSlice(d_5_a_, high), default__.PublicSlice(d_6_b_, high))

    @staticmethod
    def PublicOnly(c, high):
        source0_ = c
        if True:
            if source0_.is_Skip:
                return True
        if True:
            if source0_.is_Emit:
                d_0_isPublic_ = source0_.public
                d_1_e_ = source0_.value
                return (d_0_isPublic_) and (not(default__.Sensitive(d_1_e_, high)))
        if True:
            if source0_.is_Then:
                d_2_a_ = source0_.first
                d_3_b_ = source0_.second
                return (default__.PublicOnly(d_2_a_, high)) and (default__.PublicOnly(d_3_b_, high))
        if True:
            d_4_e_ = source0_.condition
            d_5_a_ = source0_.yes
            d_6_b_ = source0_.no
            return ((not(default__.Sensitive(d_4_e_, high))) and (default__.PublicOnly(d_5_a_, high))) and (default__.PublicOnly(d_6_b_, high))

    @staticmethod
    def ExprReads(e):
        source0_ = e
        if True:
            if source0_.is_Literal:
                d_0_v_ = source0_.value
                return _dafny.Set({})
        if True:
            if source0_.is_Input:
                d_1_i_ = source0_.slot
                return _dafny.Set({d_1_i_})
        if True:
            if source0_.is_Concat:
                d_2_a_ = source0_.left
                d_3_b_ = source0_.right
                return (default__.ExprReads(d_2_a_)) | (default__.ExprReads(d_3_b_))
        if True:
            d_4_a_ = source0_.left
            d_5_b_ = source0_.right
            return (default__.ExprReads(d_4_a_)) | (default__.ExprReads(d_5_b_))

    @staticmethod
    def CmdReads(c):
        source0_ = c
        if True:
            if source0_.is_Skip:
                return _dafny.Set({})
        if True:
            if source0_.is_Emit:
                d_0_isPublic_ = source0_.public
                d_1_e_ = source0_.value
                return default__.ExprReads(d_1_e_)
        if True:
            if source0_.is_Then:
                d_2_a_ = source0_.first
                d_3_b_ = source0_.second
                return (default__.CmdReads(d_2_a_)) | (default__.CmdReads(d_3_b_))
        if True:
            d_4_e_ = source0_.condition
            d_5_a_ = source0_.yes
            d_6_b_ = source0_.no
            return ((default__.ExprReads(d_4_e_)) | (default__.CmdReads(d_5_a_))) | (default__.CmdReads(d_6_b_))

    @staticmethod
    def CheckAndRun(types, high, values, program):
        accepted: bool = False
        trace: _dafny.Seq = _dafny.Seq({})
        accepted = (default__.Checked(program, types, high, False)) and (default__.ValidEnvironment(types, values))
        trace = _dafny.SeqWithoutIsStrInference([])
        if accepted:
            trace = default__.Run(default__.PublicSlice(program, high), values)
        return accepted, trace

    @staticmethod
    def CheckAndSlice(types, high, program):
        accepted: bool = False
        sliced: Cmd = Cmd.default()()
        accepted = default__.Checked(program, types, high, False)
        sliced = Cmd_Skip()
        if accepted:
            sliced = default__.PublicSlice(program, high)
        return accepted, sliced


class Ty:
    @_dafny.classproperty
    def AllSingletonConstructors(cls):
        return [Ty_TextTy(), Ty_FlagTy()]
    @classmethod
    def default(cls, ):
        return lambda: Ty_TextTy()
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_TextTy(self) -> bool:
        return isinstance(self, Ty_TextTy)
    @property
    def is_FlagTy(self) -> bool:
        return isinstance(self, Ty_FlagTy)

class Ty_TextTy(Ty, NamedTuple('TextTy', [])):
    def __dafnystr__(self) -> str:
        return f'Release.Ty.TextTy'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Ty_TextTy)
    def __hash__(self) -> int:
        return super().__hash__()

class Ty_FlagTy(Ty, NamedTuple('FlagTy', [])):
    def __dafnystr__(self) -> str:
        return f'Release.Ty.FlagTy'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Ty_FlagTy)
    def __hash__(self) -> int:
        return super().__hash__()


class Value:
    @classmethod
    def default(cls, ):
        return lambda: Value_Text(_dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Text(self) -> bool:
        return isinstance(self, Value_Text)
    @property
    def is_Flag(self) -> bool:
        return isinstance(self, Value_Flag)

class Value_Text(Value, NamedTuple('Text', [('text', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Value.Text({self.text.VerbatimString(True)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Value_Text) and self.text == __o.text
    def __hash__(self) -> int:
        return super().__hash__()

class Value_Flag(Value, NamedTuple('Flag', [('flag', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Value.Flag({_dafny.string_of(self.flag)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Value_Flag) and self.flag == __o.flag
    def __hash__(self) -> int:
        return super().__hash__()


class Event:
    @classmethod
    def default(cls, ):
        return lambda: Event_Emission(False, _dafny.SeqWithoutIsStrInference(map(_dafny.CodePoint, "")))
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Emission(self) -> bool:
        return isinstance(self, Event_Emission)

class Event_Emission(Event, NamedTuple('Emission', [('isPublic', Any), ('text', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Event.Emission({_dafny.string_of(self.isPublic)}, {self.text.VerbatimString(True)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Event_Emission) and self.isPublic == __o.isPublic and self.text == __o.text
    def __hash__(self) -> int:
        return super().__hash__()


class Expr:
    @classmethod
    def default(cls, ):
        return lambda: Expr_Literal(Value.default()())
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Literal(self) -> bool:
        return isinstance(self, Expr_Literal)
    @property
    def is_Input(self) -> bool:
        return isinstance(self, Expr_Input)
    @property
    def is_Concat(self) -> bool:
        return isinstance(self, Expr_Concat)
    @property
    def is_Equals(self) -> bool:
        return isinstance(self, Expr_Equals)

class Expr_Literal(Expr, NamedTuple('Literal', [('value', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Expr.Literal({_dafny.string_of(self.value)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Expr_Literal) and self.value == __o.value
    def __hash__(self) -> int:
        return super().__hash__()

class Expr_Input(Expr, NamedTuple('Input', [('slot', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Expr.Input({_dafny.string_of(self.slot)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Expr_Input) and self.slot == __o.slot
    def __hash__(self) -> int:
        return super().__hash__()

class Expr_Concat(Expr, NamedTuple('Concat', [('left', Any), ('right', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Expr.Concat({_dafny.string_of(self.left)}, {_dafny.string_of(self.right)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Expr_Concat) and self.left == __o.left and self.right == __o.right
    def __hash__(self) -> int:
        return super().__hash__()

class Expr_Equals(Expr, NamedTuple('Equals', [('left', Any), ('right', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Expr.Equals({_dafny.string_of(self.left)}, {_dafny.string_of(self.right)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Expr_Equals) and self.left == __o.left and self.right == __o.right
    def __hash__(self) -> int:
        return super().__hash__()


class Cmd:
    @classmethod
    def default(cls, ):
        return lambda: Cmd_Skip()
    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
    @property
    def is_Skip(self) -> bool:
        return isinstance(self, Cmd_Skip)
    @property
    def is_Emit(self) -> bool:
        return isinstance(self, Cmd_Emit)
    @property
    def is_Then(self) -> bool:
        return isinstance(self, Cmd_Then)
    @property
    def is_Branch(self) -> bool:
        return isinstance(self, Cmd_Branch)

class Cmd_Skip(Cmd, NamedTuple('Skip', [])):
    def __dafnystr__(self) -> str:
        return f'Release.Cmd.Skip'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Cmd_Skip)
    def __hash__(self) -> int:
        return super().__hash__()

class Cmd_Emit(Cmd, NamedTuple('Emit', [('public', Any), ('value', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Cmd.Emit({_dafny.string_of(self.public)}, {_dafny.string_of(self.value)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Cmd_Emit) and self.public == __o.public and self.value == __o.value
    def __hash__(self) -> int:
        return super().__hash__()

class Cmd_Then(Cmd, NamedTuple('Then', [('first', Any), ('second', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Cmd.Then({_dafny.string_of(self.first)}, {_dafny.string_of(self.second)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Cmd_Then) and self.first == __o.first and self.second == __o.second
    def __hash__(self) -> int:
        return super().__hash__()

class Cmd_Branch(Cmd, NamedTuple('Branch', [('condition', Any), ('yes', Any), ('no', Any)])):
    def __dafnystr__(self) -> str:
        return f'Release.Cmd.Branch({_dafny.string_of(self.condition)}, {_dafny.string_of(self.yes)}, {_dafny.string_of(self.no)})'
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Cmd_Branch) and self.condition == __o.condition and self.yes == __o.yes and self.no == __o.no
    def __hash__(self) -> int:
        return super().__hash__()

