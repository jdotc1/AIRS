"""Bounded typed integer transfer primitives for Swift outcome analysis.

No ABI result/error register is inferred here. Callers supply any entry seeds.
This is a transfer foundation, not a witness validator or compiler qualification.
Only explicit instruction kinds below have modeled effects; refusal is terminal.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
from typing import ClassVar, Mapping
from .swift_broad_instructions import (FP_DESTINATION_KINDS, GPR_DESTINATION_KINDS,
                                        FP_FLAG_KINDS, FP_MEMORY_STORES, MEMORY_WIDTHS)


class ValueKind(str, Enum):
    UNKNOWN='unknown'
    UNAVAILABLE='unavailable'
    LITERAL='literal'
    REGISTER_COPY='register_copy'
    STACK_SLOT='stack_slot'
    PHI_MERGE='phi_merge'
    DERIVED='derived'


class AbstractValue:
    """Marker for immutable abstract domain members."""


@dataclass(frozen=True)
class Unknown(AbstractValue):
    kind: ClassVar[ValueKind]=ValueKind.UNKNOWN


@dataclass(frozen=True)
class Unavailable(AbstractValue):
    kind: ClassVar[ValueKind]=ValueKind.UNAVAILABLE


@dataclass(frozen=True)
class Literal(AbstractValue):
    value: int
    width: int
    kind: ClassVar[ValueKind]=ValueKind.LITERAL
    def __post_init__(self):
        if self.width not in (32,64) or not 0 <= self.value < (1 << self.width):
            raise ValueError('literal_width')


@dataclass(frozen=True)
class RegisterCopy(AbstractValue):
    origin: str
    width: int
    kind: ClassVar[ValueKind]=ValueKind.REGISTER_COPY
    def __post_init__(self):
        if self.width not in (32,64) or not isinstance(self.origin,str):raise ValueError('register_copy_domain')


@dataclass(frozen=True)
class StackSlot(AbstractValue):
    slot: int
    epoch: int
    width: int
    kind: ClassVar[ValueKind]=ValueKind.STACK_SLOT
    def __post_init__(self):
        if self.width not in (32,64) or self.epoch<0:raise ValueError('stack_slot_domain')


@dataclass(frozen=True)
class PhiMerge(AbstractValue):
    inputs: tuple[AbstractValue,...]
    kind: ClassVar[ValueKind]=ValueKind.PHI_MERGE
    def __post_init__(self):
        if not isinstance(self.inputs,tuple) or not all(isinstance(v,AbstractValue) for v in self.inputs):raise ValueError('merge_domain')


@dataclass(frozen=True)
class Derived(AbstractValue):
    operation: str
    inputs: tuple[AbstractValue,...]
    width: int
    known_bits: tuple[int,int] | None=None
    kind: ClassVar[ValueKind]=ValueKind.DERIVED
    def __post_init__(self):
        if self.width not in (32,64) or not isinstance(self.inputs,tuple) or not all(isinstance(v,AbstractValue) for v in self.inputs):raise ValueError('derived_domain')
        if self.known_bits is not None and not isinstance(self.known_bits,tuple):raise ValueError('known_bits_domain')


@dataclass(frozen=True)
class ValueLimits:
    max_state_entries: int=128
    max_provenance_depth: int=16
    max_steps: int=4096
    max_slots: int=64
    max_merge_inputs: int=8
    max_provenance_nodes: int=4096
    max_value_inputs: int=64


@dataclass(frozen=True)
class StackCell:
    slot: int
    epoch: int
    width: int
    value: AbstractValue


def _reg(register: int | str, width=64):
    if isinstance(register,str):
        if register in ('xzr','wzr'): return 31,32 if register=='wzr' else 64
        if register in ('sp','wsp'): raise ValueError('SP is an address, not an integer register')
        if not register or register[0] not in 'xw': raise ValueError('register')
        width=32 if register[0]=='w' else 64
        register=int(register[1:])
    if not isinstance(register,int) or not 0<=register<=31 or width not in (32,64):
        raise ValueError('register')
    return register,width


def _width(value,width):
    if isinstance(value,Literal): return Literal(value.value & ((1<<width)-1),width)
    if isinstance(value,(Unknown,Unavailable)): return value
    if isinstance(value,PhiMerge):
        return PhiMerge(tuple(_width(item,width) for item in value.inputs))
    if getattr(value,'width',None)==width: return value
    return Derived('truncate' if width==32 else 'zero_extend',(value,),width)


@dataclass(frozen=True)
class ValueState:
    registers: tuple[tuple[int,AbstractValue],...]=()
    register_epochs: tuple[tuple[int,int],...]=()
    stack: tuple[StackCell,...]=()
    sp_offset: int | None=0
    stack_epoch: int=0
    steps: int=0
    refusal: str | None=None

    def read_register(self,register: int | str,width=64):
        register,width=_reg(register,width)
        return Literal(0,width) if register==31 else _width(dict(self.registers).get(register,Unknown()),width)


@dataclass(frozen=True)
class TransferResult:
    state: ValueState
    status: str='resolved'
    reason: str | None=None


def _depth_ok(value,limit):
    # Iterative and bounded: avoid recursive traversal of caller-supplied trees.
    todo=[(value,1)]; visited=0
    while todo:
        node,depth=todo.pop(); visited+=1
        if depth>limit or visited>4096: return False
        inputs=getattr(node,'inputs',())
        if len(inputs)>4096-len(todo): return False
        todo.extend((child,depth+1) for child in inputs)
    return True


def _state_issue(state,limits,*,budget=None):
    """Iterative aggregate preflight before normalization or structural equality."""
    if state.refusal:return state.refusal
    if len(state.registers)+len(state.stack)>limits.max_state_entries or len(state.stack)>limits.max_slots:
        return 'value_state_limit'
    if len(state.register_epochs)>31:return 'value_state_limit'
    todo=[]
    for _,value in state.registers:todo.append((value,1))
    for cell in state.stack:todo.append((cell.value,1))
    budget=[limits.max_provenance_nodes] if budget is None else budget
    while todo:
        node,depth=todo.pop();budget[0]-=1
        if not isinstance(node,AbstractValue) or depth>limits.max_provenance_depth or budget[0]<0:
            return 'value_provenance_limit'
        inputs=getattr(node,'inputs',())
        if len(inputs)>limits.max_value_inputs or len(inputs)+len(todo)>budget[0]:
            return 'value_provenance_limit'
        todo.extend((child,depth+1) for child in inputs)
    return None


def initial_state(registers: Mapping[int | str,AbstractValue] | None=None,*,limits=ValueLimits()):
    registers=registers or {}
    if len(registers)>min(31,limits.max_state_entries): raise ValueError('state_entry_limit')
    result={}
    for key,value in registers.items():
        reg,width=_reg(key)
        if not isinstance(value,AbstractValue) or not _depth_ok(value,limits.max_provenance_depth):
            raise ValueError('value_provenance_limit')
        if reg!=31: result[reg]=_width(_width(value,width),64)
    return ValueState(tuple(sorted(result.items())))


def _transfer_swift_value(state: ValueState,instruction,*,limits=ValueLimits())->TransferResult:
    """Apply one decoded primitive. On refusal return the unchanged input state."""
    def refuse(reason): return TransferResult(state,'unresolved',reason)
    issue=_state_issue(state,limits)
    if issue:return refuse(issue)
    if state.steps>=limits.max_steps: return refuse('value_step_limit')
    if len(state.registers)+len(state.stack)>limits.max_state_entries or len(state.stack)>limits.max_slots:
        return refuse('value_state_limit')
    if any(not _depth_ok(value,limits.max_provenance_depth) for _,value in state.registers):
        return refuse('value_provenance_limit')
    registers=dict(state.registers); epochs=dict(state.register_epochs)
    stack=list(state.stack); sp=state.sp_offset; epoch=state.stack_epoch
    kind=instruction.kind; width=32 if kind.startswith('w') else 64
    rd,rn=instruction.rd,instruction.rn
    def read(reg,bits=width): return state.read_register(reg,bits)
    def write(reg,value,bits=width):
        if reg==31:return
        if reg not in registers and len(registers)+len(stack)>=limits.max_state_entries:
            raise _ValueRefusal('value_state_limit')
        if not _depth_ok(value,limits.max_provenance_depth):
            raise _ValueRefusal('value_provenance_limit')
        registers[reg]=_width(_width(value,bits),64)
        epochs[reg]=epochs.get(reg,0)+1
    def adjust(new_sp):
        nonlocal sp,stack,epoch
        if new_sp is None:
            stack=[];epoch+=1
        elif sp is not None and new_sp>sp:
            stack=[cell for cell in stack if cell.slot>=new_sp];epoch+=1
        sp=new_sp
    def stack_address(value):
        if isinstance(value,Derived) and value.operation=='entry_sp_offset' and len(value.inputs)==1 and isinstance(value.inputs[0],Literal):
            number=value.inputs[0].value
            return number-(1<<64) if number & (1<<63) else number
        return None
    if kind in FP_DESTINATION_KINDS or kind in FP_FLAG_KINDS:
        # The scalar GPR/stack domain does not evaluate FP values or NZCV.
        # Exact descriptors prove these forms cannot overwrite a GPR or SP.
        pass
    elif kind in MEMORY_WIDTHS:
        load=kind in ('wldrb','wldrh','xldr_raw','xldur','wldr_raw','wldur')
        base=sp if rn==31 else stack_address(read(rn,64))
        size=MEMORY_WIDTHS[kind]
        offset=None if base is None else base+instruction.immediate
        if load:
            cell=next((c for c in stack if c.slot==offset and c.width==size*8),None)
            value=cell.value if cell is not None and size in (4,8) else Unknown()
            write(rd,value,32 if size<8 else 64)
        else:
            if base is None:
                stack=[]
            else:
                stack=[cell for cell in stack if cell.slot+cell.width//8<=offset or cell.slot>=offset+size]
            epoch+=1
            if kind not in FP_MEMORY_STORES and size in (4,8) and offset is not None and sp is not None and sp<=offset and offset+size<=0:
                if len(stack)>=limits.max_slots or len(registers)+len(stack)>=limits.max_state_entries:
                    return refuse('value_slot_limit')
                stack.append(StackCell(offset,epoch,size*8,read(rd,size*8)))
    elif kind in ('xadd_reg','xsub_reg','wadd_reg','wsub_reg',
                  'xadds_reg','xsubs_reg','wadds_reg','wsubs_reg','wand_reg','xand_reg'):
        shift=instruction.immediate; shift_kind=instruction.addressing
        if type(shift) is not int or not 0<=shift<width or shift_kind not in ('lsl','lsr','asr'):
            return refuse('register_shift_unqualified')
        left,right=read(rn),read(instruction.rt2)
        if isinstance(right,Literal):
            number=right.value
            if shift_kind=='lsl':number<<=shift
            elif shift_kind=='lsr':number>>=shift
            else:
                if number & (1<<(width-1)):number-=1<<width
                number>>=shift
            right=Literal(number&((1<<width)-1),width)
        elif shift and not isinstance(right,(Unknown,Unavailable)):
            right=Derived(shift_kind,(right,Literal(shift,width)),width)
        op='and' if 'and' in kind else ('sub' if 'sub' in kind else 'add')
        if isinstance(left,Literal) and isinstance(right,Literal):
            number=(left.value&right.value if op=='and' else
                    left.value+right.value if op=='add' else left.value-right.value)
            value=Literal(number&((1<<width)-1),width)
        elif isinstance(left,(Unknown,Unavailable)) or isinstance(right,(Unknown,Unavailable)):value=Unknown()
        else:value=Derived(op,(left,right),width)
        # These shifted-register forms treat register31 as ZR, including CMP.
        # NZCV is not modeled, and a discarded Rd31 does not write SP.
        write(rd,value)
    elif kind in ('xadd_ext','xsub_ext'):
        modes={'uxtb':8,'uxth':16,'uxtw':32,'uxtx':64,
               'sxtb':8,'sxth':16,'sxtw':32,'sxtx':64}
        mode=instruction.addressing; shift=instruction.immediate
        if mode not in modes or type(shift) is not int or not 0<=shift<=4:
            return refuse('register_extend_unqualified')
        bits=modes[mode];right=read(instruction.rt2,64)
        if isinstance(right,Literal):
            number=right.value&((1<<bits)-1)
            if mode.startswith('s') and number&(1<<(bits-1)):number-=1<<bits
            number<<=shift
            right=Literal(number&((1<<64)-1),64)
        elif not isinstance(right,(Unknown,Unavailable)):
            right=Derived('extend_'+mode,(right,Literal(shift,64)),64)
        frame=sp if rn==31 else stack_address(read(rn,64))
        if rn==31 or frame is not None:
            if frame is None or not isinstance(right,Literal):offset=None
            else:
                delta=right.value-(1<<64) if right.value&(1<<63) else right.value
                offset=frame+(-delta if kind=='xsub_ext' else delta)
            if rd==31:adjust(offset)
            elif offset is None:write(rd,Unknown(),64)
            else:write(rd,Derived('entry_sp_offset',(Literal(offset&((1<<64)-1),64),),64),64)
        elif rd==31:
            # A non-frame integer cannot establish an entry-relative SP.
            adjust(None)
        else:
            left=read(rn,64);op='sub' if kind=='xsub_ext' else 'add'
            if isinstance(left,Literal) and isinstance(right,Literal):
                value=Literal((left.value-right.value if op=='sub' else left.value+right.value)&((1<<64)-1),64)
            elif isinstance(left,(Unknown,Unavailable)) or isinstance(right,(Unknown,Unavailable)):value=Unknown()
            else:value=Derived(op,(left,right),64)
            write(rd,value,64)
    elif kind in GPR_DESTINATION_KINDS:
        # Address materialization, FP bit transfers and FP conversions do not
        # establish integer origins in this domain. Forget the exact target.
        write(rd,Unknown(),32 if kind.startswith('fmov_w') or kind.startswith('fcvtzs_w') else 64)
    elif kind=='brk':return refuse('exception_transfer_effect_unqualified')
    elif kind in ('nop','ret','b','bcond','wcbz','wcbnz','xcbz','xcbnz','wtbz','wtbnz','xtbz','xtbnz'):
        pass
    elif kind=='bl':
        for reg in (*range(19),30): write(reg,Unknown(),64)
        stack=[];epoch+=1
    elif kind in ('mov','wmov'):
        write(rd,read(rn))
    elif kind in ('movz','movn','wmovz','wmovn'):
        literal=instruction.immediate
        # Decoder MOVZ/MOVN fields are a single shifted 16-bit lane.
        if (not isinstance(literal,int) or literal<0 or
                not any(literal & ~(0xffff<<shift)==0 for shift in range(0,width,16))):
            return refuse('move_immediate_unqualified')
        if kind.endswith('movn'): literal=~literal
        write(rd,Literal(literal & ((1<<width)-1),width))
    elif kind in ('xmovk','wmovk'):
        # Decoder encodes lane shift in addressing and unshifted immediate.
        if not isinstance(instruction.immediate,int) or not 0<=instruction.immediate<=0xffff:
            return refuse('move_immediate_unqualified')
        try: shift=int(instruction.addressing)
        except ValueError:return refuse('move_lane_unqualified')
        if shift not in range(0,width,16):return refuse('move_lane_unqualified')
        old=read(rd)
        if isinstance(old,Literal):
            write(rd,Literal((old.value & ~(0xffff<<shift)) | (instruction.immediate<<shift),width))
        else: write(rd,Derived('insert_lane',(old,Literal(instruction.immediate,width),Literal(shift,width)),width))
    elif kind in ('add','sub','wadd','wadds','wsubs','xadds','xsubs','wlsl'):
        if rn==31 and kind in ('wadd','wadds','wsubs','xadds','xsubs'):
            return refuse('stack_address_integer_unqualified')
        if kind=='wadd' and rd==31:return refuse('wsp_adjustment_unqualified')
        if kind in ('add','sub') and (rn==31 or stack_address(read(rn)) is not None):
            base=sp if rn==31 else stack_address(read(rn))
            offset=None if base is None else base+(instruction.immediate if kind=='add' else -instruction.immediate)
            if rd==31:adjust(offset)
            elif offset is None:write(rd,Unknown())
            else:write(rd,Derived('entry_sp_offset',(Literal(offset & ((1<<64)-1),64),),64))
        elif rd==31 and kind in ('add','sub'):
            return refuse('unknown_stack_adjustment')
        else:
            source=read(rn); imm=instruction.immediate
            operation='lsl' if kind=='wlsl' else ('sub' if 'sub' in kind else 'add')
            if operation=='lsl' and not 0<=imm<width:return refuse('shift_unqualified')
            if isinstance(source,Literal):
                number=source.value
                number=(number<<imm) if operation=='lsl' else (number-imm if operation=='sub' else number+imm)
                value=Literal(number & ((1<<width)-1),width)
            elif isinstance(source,(Unknown,Unavailable)):value=source
            else:value=Derived(operation,(source,Literal(imm & ((1<<width)-1),width)),width)
            write(rd,value)
    elif kind in ('wand_imm','xand_imm','worr_imm','xorr_imm','weor_imm','xeor_imm','wands_imm','xands_imm'):
        mask=instruction.immediate
        if type(mask) is not int or not 0<=mask<(1<<width):return refuse('logical_mask_unqualified')
        source=read(rn)
        operation='and' if 'and' in kind else ('or' if 'orr' in kind else 'xor')
        if isinstance(source,Literal):
            number=(source.value&mask if operation=='and' else
                    source.value|mask if operation=='or' else source.value^mask)
            value=Literal(number&((1<<width)-1),width)
        elif isinstance(source,(Unknown,Unavailable)):value=source
        else:value=Derived(operation,(source,Literal(mask,width)),width)
        write(rd,value)
    elif kind in ('wcsel','xcsel','wcsinc','xcsinc','wcsinv','xcsinv','wcsneg','xcsneg'):
        # NZCV is not in this integer domain. A known conditional write still
        # invalidates its GPR destination without inventing a chosen value.
        write(rd,Unknown())
    elif kind in ('xubfm','wubfm'):
        try:rotate=int(instruction.addressing)
        except ValueError:return refuse('bitfield_unqualified')
        end=instruction.immediate
        if not 0<=rotate<width or not 0<=end<width:return refuse('bitfield_unqualified')
        source=read(rn)
        if isinstance(source,Literal):
            number=((source.value>>rotate)&((1<<(end-rotate+1))-1) if end>=rotate
                    else (source.value&((1<<(end+1))-1))<<(width-rotate))
            value=Literal(number&((1<<width)-1),width)
        elif isinstance(source,(Unknown,Unavailable)):value=source
        else:value=Derived('unsigned_bitfield',(source,Literal(rotate,width),Literal(end,width)),width)
        write(rd,value)
    elif kind in ('xsbfm','wsbfm'):
        if instruction.addressing!='0' or not 0<=instruction.immediate<width:
            return refuse('bitfield_unqualified')
        source=read(rn); bits=instruction.immediate+1
        if isinstance(source,Literal):
            number=source.value & ((1<<bits)-1)
            if number & (1<<(bits-1)):number-=1<<bits
            value=Literal(number & ((1<<width)-1),width)
        elif isinstance(source,(Unknown,Unavailable)):value=source
        else:value=Derived('sign_extend',(source,Literal(bits,width)),width)
        write(rd,value)
    elif kind in ('xstr','wstr','xldr','wldr','xldr_post','stp','ldp'):
        pair=kind in ('stp','ldp'); load=kind in ('xldr','wldr','xldr_post','ldp')
        regs=(rd,instruction.rt2) if pair else (rd,)
        mode=instruction.addressing or 'offset'
        if mode not in ('offset','pre','post'):return refuse('memory_mode_unqualified')
        if load and len(set(regs))!=len(regs):return refuse('memory_register_overlap')
        if mode in ('pre','post') and rn!=31 and rn in regs:
            return refuse('memory_register_overlap')
        base=sp if rn==31 else stack_address(read(rn,64))
        if base is None or sp is None:return refuse('stack_base_unqualified')
        count=2 if pair else 1;size=width//8
        offset=base+(0 if mode=='post' else instruction.immediate)
        if mode=='pre' and rn==31:adjust(offset)
        if offset<sp or offset+size*count>0:return refuse('memory_outside_frame')
        if not load:
            # Capacity checked before constructing any new cells.
            retained=[c for c in stack if c.slot+c.width//8<=offset or c.slot>=offset+size*count]
            if len(retained)+count>limits.max_slots:return refuse('value_slot_limit')
            if len(registers)+len(retained)+count>limits.max_state_entries:return refuse('value_state_limit')
            epoch+=1
            stack=retained+[StackCell(offset+i*size,epoch,width,read(reg)) for i,reg in enumerate(regs)]
        else:
            for i,reg in enumerate(regs):
                cell=next((c for c in stack if c.slot==offset+i*size and c.width==width),None)
                write(reg,cell.value if cell else Unknown())
        if mode in ('pre','post'):
            next_base=base+instruction.immediate
            if rn==31:
                if mode=='post':adjust(next_base)
            else:write(rn,Derived('entry_sp_offset',(Literal(next_base&((1<<64)-1),64),),64),64)
    else:return refuse('instruction_effect_unqualified')
    if len(registers)+len(stack)>limits.max_state_entries:return refuse('value_state_limit')
    if any(not _depth_ok(value,limits.max_provenance_depth) for value in registers.values()):
        return refuse('value_provenance_limit')
    return TransferResult(ValueState(tuple(sorted(registers.items())),tuple(sorted(epochs.items())),tuple(stack),sp,epoch,state.steps+1))


class _ValueRefusal(Exception):
    pass


def transfer_swift_value(state: ValueState,instruction,*,limits=ValueLimits())->TransferResult:
    """Apply one exact primitive; all bounds refusals preserve the input state."""
    try:
        return _transfer_swift_value(state,instruction,limits=limits)
    except _ValueRefusal as error:
        return TransferResult(state,'unresolved',str(error))


def join_swift_values(states,*,limits=ValueLimits())->ValueState:
    """Conservative finite join; missing evidence is unknown, never zero."""
    # Bound input consumption, including generators, before materialization.
    bounded=[]
    budget=[limits.max_provenance_nodes]
    def refused(reason,extra=None):
        observed=bounded if extra is None else (*bounded,extra)
        return ValueState(sp_offset=None,steps=max((limits.max_steps,*(s.steps for s in observed))),
                          stack_epoch=max((0,*(s.stack_epoch for s in observed))),refusal=reason)
    for state in states:
        if len(bounded)>=limits.max_merge_inputs:return refused('value_join_limit',state)
        issue=_state_issue(state,limits,budget=budget)
        if issue:return refused(issue,state)
        bounded.append(state)
    if not bounded:return refused('value_join_empty')
    keys=set().union(*(dict(s.registers) for s in bounded))
    if len(keys)>limits.max_state_entries:return refused('value_state_limit')
    registers=[]
    for reg in sorted(keys):
        values=[]
        for state in bounded:
            value=state.read_register(reg)
            if value not in values:values.append(value)
        if len(values)==1:value=values[0]
        elif any(isinstance(v,(Unknown,Unavailable)) for v in values):value=Unknown()
        elif len(values)>limits.max_merge_inputs:value=Unknown()
        elif any(not _depth_ok(v,limits.max_provenance_depth-1) for v in values):value=Unknown()
        else:value=PhiMerge(tuple(values))
        registers.append((reg,value))
    first=bounded[0]
    stack=tuple(c for c in first.stack if all(c in s.stack for s in bounded[1:]))
    sp=first.sp_offset if all(s.sp_offset==first.sp_offset for s in bounded) else None
    if sp is None:stack=()
    epochs=tuple((reg,max(dict(s.register_epochs).get(reg,0) for s in bounded)) for reg in keys)
    result=ValueState(tuple(registers),epochs,stack,sp,max(s.stack_epoch for s in bounded),max(s.steps for s in bounded))
    issue=_state_issue(result,limits)
    return refused(issue) if issue else result


def trace_swift_values(instructions,*,state=None,limits=ValueLimits())->TransferResult:
    """Consume at most the step budget, stopping at the first refused primitive."""
    state=state if state is not None else initial_state(limits=limits)
    for instruction in instructions:
        result=transfer_swift_value(state,instruction,limits=limits)
        if result.status!='resolved':return result
        state=result.state
    return TransferResult(state)
