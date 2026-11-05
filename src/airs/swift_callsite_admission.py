"""Offline exact call-target admission. Syntax and ABI remain independent claims.

BLR is admitted only from a bounded, straight-line entry-prefix constant proof
and an independently read selected-image entry screen. Dispatch syntax alone
never proves a vtable/witness target. Records bind every byte read, without rehashing an
already admitted image. Consumers must check the binding before using a record
against a different image object.
"""
from dataclasses import dataclass, asdict
import struct
from .types import Section, FunctionRange, MachOImage
from types import MappingProxyType
from bisect import bisect_right


@dataclass(frozen=True, slots=True)
class CallsiteLimits:
    max_work: int = 100000
    max_window_instructions: int = 64
    max_entry_screen_instructions: int = 4096
    max_aliases: int = 16
    max_records: int = 10000
    max_symbol_bytes: int = 4096
    max_load_commands: int = 4096

    def __post_init__(self):
        if any(type(getattr(self,k)) is not int or getattr(self,k)<0 for k in self.__dataclass_fields__):
            raise ValueError('callsite limits must be nonnegative integers')


class _Stop(Exception):
    def __init__(self, reason, incomplete=False):
        self.reason,self.incomplete=reason,incomplete


def _identity(image):
    return dict(slice_sha256=image.slice_sha256,container_sha256=image.container_sha256,
                slice_offset=image.slice_offset,slice_size=image.slice_size,
                architecture=image.architecture,cpu_subtype=image.cpu_subtype,
                preferred_base=image.preferred_base,file_type=image.file_type)


def callsite_binding_matches(image, record, *, session=None):
    """Cheap exact-byte binding check, not a source/signature verification pass."""
    try:
        binding=record['binding']
        if binding['image'] != _identity(image): return False
        if binding.get('session_required'):
            if not _session_matches(image,session): return False
        else:
            if binding['functions'] != [asdict(f) for f in image.functions]: return False
            if binding['sections'] != [asdict(s) for s in image.sections]: return False
        for offset,raw in binding['reads']:
            expected=bytes.fromhex(raw)
            if image.data[offset:offset+len(expected)] != expected: return False
        return True
    except (KeyError,ValueError,TypeError,AttributeError): return False


def _bound_metadata(image, limits, need, charge):
    need(type(image) is MachOImage and type(image.data) is bytes and
         type(image.functions) is tuple and type(image.sections) is tuple,'immutable_image_required')
    need(type(image.slice_offset) is int and 0<=image.slice_offset<2**64
         and type(image.slice_size) is int and image.slice_size==len(image.data),'selected_slice_extent')
    need(image.architecture=='arm64' and image.cpu_subtype in (0,1),'architecture_unsupported')
    charge(len(image.functions)+len(image.sections))
    need(len(image.functions)<=limits.max_records and len(image.sections)<=limits.max_records,'metadata_record_limit',True)
    for row in (*image.functions,*image.sections):
        charge();need(type(row) in (FunctionRange,Section),'immutable_metadata_required')
    # Bound serialized metadata as well as the number of metadata records.
    for row in (*image.functions,*image.sections):
        charge()
        for key in row.__dataclass_fields__:
            charge()
            value=getattr(row,key)
            if isinstance(value,str):
                need(len(value)<=limits.max_symbol_bytes,'metadata_name_limit',True)
                charge(len(value))
    for value in (image.slice_sha256,image.container_sha256,image.architecture):
        charge()
        need(isinstance(value,str) and len(value)<=limits.max_symbol_bytes,'metadata_name_limit',True)
        charge(len(value))


def _parse_raw_metadata(image, limits, need, charge, read, unpack):
    magic,cpu,subtype,file_type,ncmds,sizeofcmds,_,_=unpack('<8I',0)
    need(magic==0xfeedfacf and cpu==0x100000c and subtype==image.cpu_subtype
         and file_type==image.file_type,'selected_slice_header')
    need(ncmds<=limits.max_load_commands,'load_command_limit',True)
    need(32+sizeofcmds<=image.slice_size,'load_command_extent')
    cursor=32;table=None;function_table=None;raw_sections=[];base=None
    for _ in range(ncmds):
        charge();command,size=unpack('<II',cursor)
        need(size>=8 and size%8==0 and cursor+size<=32+sizeofcmds,'load_command_extent')
        if command==2:
            need(table is None and size==24,'symbol_table_ambiguous')
            table=unpack('<IIII',cursor+8)
        elif command==0xb:
            need(size==80,'dynamic_symbol_table_extent')
            external_relocations,=unpack('<I',cursor+68)
            local_relocations,=unpack('<I',cursor+76)
            need(external_relocations==local_relocations==0,'relocations_unsupported')
        elif command==0x29:
            need(size==16,'embedded_data_command')
            _,embedded_size=unpack('<II',cursor+8)
            need(embedded_size==0,'embedded_data_unsupported')
        elif command==0x2c:
            need(size==24,'encryption_command')
            _,_,cryptid,_=unpack('<IIII',cursor+8)
            need(cryptid==0,'encrypted_image')
        elif command==0x26:
            need(function_table is None and size==16,'function_starts_command')
            function_table=unpack('<II',cursor+8)
        elif command==0x19:
            need(size>=72,'segment_extent')
            _,_,segment,vmaddr,vmsize,fileoff,filesize,maxprot,initprot,sections,_=unpack('<II16sQQQQiiII',cursor)
            need(sections<=limits.max_records and 72+80*sections==size,'section_record_limit',True)
            need(vmaddr+vmsize<=2**64 and fileoff+filesize<=image.slice_size
                 and initprot&~maxprot==0,'segment_mapping')
            if segment.rstrip(b'\0')==b'__TEXT':
                need(base is None,'text_segment_ambiguous');base=vmaddr
            for j in range(sections):
                charge()
                name,seg,address,extent,offset,align,_,relocations,flags,_,_,_=unpack('<16s16sQQIIIIIIII',cursor+72+80*j)
                need(relocations==0,'relocations_unsupported')
                try:
                    name=name.split(b'\0',1)[0].decode('ascii');seg=seg.split(b'\0',1)[0].decode('ascii')
                except UnicodeDecodeError: raise _Stop('section_name_encoding')
                section=Section(seg,name,address,extent,offset,flags)
                need(vmaddr<=address<=address+extent<=vmaddr+vmsize,'section_mapping')
                if section.executable:
                    need(initprot&4 and flags&255 not in (1,12,18),'section_mapping')
                    need(address-vmaddr==offset-fileoff and fileoff<=offset<=offset+extent<=fileoff+filesize
                         and offset>=32+sizeofcmds,'section_mapping')
                raw_sections.append(section)
                need(len(raw_sections)<=limits.max_records,'section_record_limit',True)
        cursor+=size
    need(cursor==32+sizeofcmds,'load_command_extent')
    charge(len(raw_sections)+len(image.sections))
    need(tuple(raw_sections)==image.sections and base==image.preferred_base,'raw_section_metadata_mismatch')
    need(function_table is not None,'function_starts_missing')
    start_offset,start_size=function_table
    payload=read(start_offset,start_size);position=0;address=base;starts=[];terminated=False
    while position<len(payload):
        charge();value=0
        for index in range(10):
            charge();need(position<len(payload),'function_starts_uleb')
            byte=payload[position];position+=1
            need(index<9 or byte&0xfe==0,'function_starts_uleb')
            value|=(byte&127)<<(7*index)
            if byte<128: break
        else: raise _Stop('function_starts_uleb')
        if value==0:
            charge(len(payload)-position)
            need(not any(payload[position:]),'function_starts_trailing_data');terminated=True;break
        address+=value
        need(address<2**64 and address%4==0,'function_starts_address')
        need(len(starts)<limits.max_records,'function_record_limit',True)
        starts.append(address)
    need(terminated,'function_starts_terminator')
    charge(len(starts)+len(image.functions))
    need(starts==[f.start for f in image.functions],'raw_function_metadata_mismatch')
    for i,function in enumerate(image.functions):
        charge(len(raw_sections)+1)
        matching=[section for section in raw_sections if section.executable and section.address<=function.start<section.end]
        need(len(matching)==1,'function_starts_mapping')
        expected_end=matching[0].end
        if i+1<len(starts): expected_end=min(expected_end,starts[i+1])
        need(function.end==expected_end and function.boundary_source=='lc_function_starts','raw_function_metadata_mismatch')
    need(table is not None,'callee_symbols_missing')
    offset,count,strings,string_size=table
    need(count<=limits.max_records,'symbol_record_limit',True)
    need(offset+count*16<=image.slice_size and strings+string_size<=image.slice_size,'symbol_table_extent')
    return table


def admit_broad_swift_callsite(image, caller, call_pc: int, *, limits=CallsiteLimits(), abi_profile=None, session=None) -> dict:
    """Admit an exact local direct target, never a post-call outcome or ABI fact."""
    result=dict(model_version='swift-broad-callsite-v1',status='declined',reason='',
                details_complete=True,abi_admitted=False,call_return_proven=False,
                error_state_proven=False,syntactic_call_target_admitted=False,exclusive_entry_proven=False,
                provenance={},work_steps=0,
                abi=dict(status='unresolved',reason='separate_abi_admission_required'))
    reads=[];work=0
    def need(ok,reason,incomplete=False):
        if not ok: raise _Stop(reason,incomplete)
    def charge(n=1):
        nonlocal work
        need(n<=limits.max_work-work,'callsite_work_limit',True);work+=n
    def read(offset,size):
        charge(size+1)
        need(type(offset) is int and 0<=offset and 0<=size and offset+size<=len(image.data)
             and offset+size<=image.slice_size,'selected_slice_mapping')
        raw=image.data[offset:offset+size];reads.append((offset,raw.hex()));return raw
    def unpack(fmt,offset):
        return struct.unpack(fmt,read(offset,struct.calcsize(fmt)))
    def instruction(pc):
        need(0<=pc<=2**64-4 and pc%4==0,'instruction_address')
        found=[]
        for section in image.sections:
            charge()
            if section.address<=pc and pc+4<=section.end: found.append(section)
        need(len(found)==1,'instruction_mapping_ambiguous')
        section=found[0]
        need(section.executable and section.flags&255 not in (1,8,12,18)
             and 'stub' not in section.name.lower(),'instruction_not_executable')
        offset=section.file_offset+pc-section.address
        raw=read(offset,4)
        return int.from_bytes(raw,'little'),dict(pc=pc,word=f'0x{int.from_bytes(raw,"little"):08x}',
            slice_file_offset=offset,container_file_offset=image.slice_offset+offset),section
    def constant_target(register):
        # No backward pattern search: every prefix instruction participates.
        count=(call_pc-caller.start)//4
        need(0<count<limits.max_window_instructions,'indirect_target_unresolved')
        constants={};proof=[]
        for pc in range(caller.start,call_pc,4):
            charge();w,record,_=instruction(pc);proof.append(record);rd=w&31
            value=None
            if w==0xd503201f: continue
            if w&0x1f000000==0x10000000:  # ADR or ADRP, signed 21-bit immediate
                immediate=((w>>5)&0x7ffff)*4+((w>>29)&3)
                if immediate&(1<<20): immediate-=1<<21
                value=((pc&~4095)+(immediate<<12)) if w>>31 else pc+immediate
            elif w&0xff800000==0x91000000:  # ADD Xd,Xn,#imm{,lsl #12}
                rn=(w>>5)&31
                if rn in constants:
                    value=constants[rn]+(((w>>10)&4095)<<(12 if w&(1<<22) else 0))
            elif w&0xff800000 in (0xd2800000,0x92800000,0xf2800000):
                shift=((w>>21)&3)*16;immediate=((w>>5)&65535)<<shift
                if w&0xff800000==0xd2800000: value=immediate
                elif w&0xff800000==0x92800000: value=(~immediate)&((1<<64)-1)
                elif rd in constants: value=(constants[rd]&~(65535<<shift))|immediate
            elif w&0xffe0ffe0==0xaa0003e0:  # MOV Xd,Xm; no shifted ORR aliases
                rm=(w>>16)&31;value=0 if rm==31 else constants.get(rm)
            elif (w&0xffe0ffe0==0x2a0003e0 or
                  w&0xff800000 in (0x52800000,0x12800000,0x72800000,0x11000000)):
                # Deliberately invalidate the corresponding X register on a W write.
                value=None
            else: raise _Stop('indirect_target_unresolved')
            if value is not None: need(0<=value<2**64,'indirect_constant_overflow')
            if rd!=31:
                if value is None: constants.pop(rd,None)
                else: constants[rd]=value
        need(register in constants,'indirect_target_unresolved')
        result['provenance']['target_constant']=dict(register=f'x{register}',value=constants[register],
            model='straight_line_caller_entry_constant_v1',instructions=proof)
        return constants[register]

    def screen_indirect_entries():
        # This is bounded syntactic selected-image evidence, not an assertion
        # that foreign images or runtime-patched code cannot supply an entry.
        charge(len(image.sections))
        count=sum(section.size//4 for section in image.sections if section.executable)
        need(count<=limits.max_entry_screen_instructions,'indirect_entry_screen_limit',True)
        screened=[]
        for section in image.sections:
            charge()
            if not section.executable: continue
            need(section.address%4==0 and section.size%4==0,'indirect_entry_screen_unresolved')
            for pc in range(section.address,section.end,4):
                charge();w,record,_=instruction(pc);screened.append(record)
                destination=None
                if w&0x7c000000==0x14000000:
                    immediate=w&0x3ffffff
                    if immediate&0x2000000: immediate-=0x4000000
                    destination=pc+immediate*4
                elif w&0xff000000==0x54000000 or w&0x7e000000==0x34000000:
                    immediate=(w>>5)&0x7ffff
                    if immediate&0x40000: immediate-=0x80000
                    destination=pc+immediate*4
                elif w&0x7e000000==0x36000000:
                    immediate=(w>>5)&0x3fff
                    if immediate&0x2000: immediate-=0x4000
                    destination=pc+immediate*4
                elif w&0xfe000000==0xd6000000:
                    need(pc==call_pc or w==0xd65f03c0,'indirect_entry_screen_unresolved')
                if destination is not None:
                    need(not caller.start<destination<=call_pc,'indirect_window_incoming_edge')
        result['provenance']['entry_screen']=dict(model='selected_image_direct_edges_and_symbol_entries_v1',
            scope='selected_image_only',instructions=screened)

    try:
        need(type(call_pc) is int and call_pc%4==0,'call_pc_alignment')
        if session is None:
            _bound_metadata(image,limits,need,charge)
        else:
            charge();need(_session_matches(image,session),'callsite_session_image_mismatch')
            need(session._record_count<=limits.max_records,'metadata_record_limit',True)
            need(session._limits.max_load_commands<=limits.max_load_commands,'load_command_limit',True)
            need(session._limits.max_symbol_bytes<=limits.max_symbol_bytes,'metadata_name_limit',True)
        if session is not None: charge()
        need(type(caller) is FunctionRange,'caller_exact_membership')
        need((caller in image.functions if session is None else session._function_index.get(caller.start) is caller) and caller.boundary_source=='lc_function_starts'
             and 0<=caller.start<caller.end<=2**64 and caller.start%4==0 and caller.end%4==0,'caller_exact_membership')
        need(caller.start<=call_pc and call_pc+4<=caller.end,'call_pc_outside_caller')
        if session is None:
            charge(len(image.functions))
            need(sum(f.start<=call_pc<f.end for f in image.functions)==1,'caller_overlap')
        need(limits.max_window_instructions>=1,'instruction_window_limit',True)
        word,provenance,call_section=instruction(call_pc)
        result['provenance']['call']=provenance
        indirect=word&0xfffffc1f==0xd63f0000
        if word&0xfffffc1f==0xd61f0000: raise _Stop('indirect_target_unresolved')
        if word&0xfe000000==0xd6000000 and word&0x00200000 and not indirect:
            raise _Stop('authenticated_indirect_unsupported')
        if indirect:
            tail=False;target=constant_target((word>>5)&31);kind='blr_constant'
        else:
            need(word&0x7c000000==0x14000000,'instruction_not_direct_call')
            tail=not bool(word&0x80000000)
            displacement=(word&0x3ffffff)
            if displacement&0x2000000: displacement-=0x4000000
            target=call_pc+displacement*4;kind='b' if tail else 'bl'
        need(0<=target<=2**64-4 and target%4==0,'call_target_overflow')
        result.update(call_pc=call_pc,callee_pc=target,call_kind=kind,
                      caller_start=caller.start,caller_end=caller.end)
        if session is None:
            charge(2*len(image.functions))
            matches=[f for f in image.functions if f.start==target and f.boundary_source=='lc_function_starts']
        else:
            charge();matches=[session._function_index[target]] if target in session._function_index else []
        need(len(matches)==1 and matches[0].end>target,'callee_exact_entry_required')
        if session is None:
            need(sum(f.start<=target<f.end for f in image.functions)==1,'callee_overlap')
        _,entry_provenance,target_section=instruction(target)
        result['provenance']['callee_entry']=entry_provenance
        if session is None:
            table=_parse_raw_metadata(image,limits,need,charge,read,unpack)
        else:
            table=session._table
        offset,count,strings,string_size=table
        if indirect: screen_indirect_entries()
        aliases=[];symbol_records=[]
        if session is None:
            rows=[]
            for i in range(count):
                charge();row=unpack('<IBBHQ',offset+16*i)
                if indirect and not row[1]&0xe0:
                    need(not caller.start<row[4]<=call_pc,'indirect_window_symbol_entry')
                if row[4]==target: rows.append((i,row))
        else:
            charge();rows=session._symbol_index.get(target,())
            if indirect:
                charge(max(1,len(session._entry_values).bit_length()))
                index=bisect_right(session._entry_values,caller.start)
                need(index==len(session._entry_values) or session._entry_values[index]>call_pc,
                     'indirect_window_symbol_entry')
        for i,row in rows:
            charge();sx,kind,section_index,desc,value=row
            # All records naming the entry participate, including contradictory aliases.
            if value!=target: continue
            need(len(aliases)<limits.max_aliases,'alias_limit',True)
            need((kind==15 and not desc&0x380) or (kind==14 and desc==0)
                 or (kind==30 and desc in (0,0x80) and result['call_kind']=='bl'),'callee_visibility')
            need(1<=section_index<=len(image.sections) and image.sections[section_index-1]==target_section,'callee_symbol_section')
            need(0<sx<string_size,'callee_symbol_extent')
            n=min(string_size-sx,limits.max_symbol_bytes+1)
            raw=read(strings+sx,n);end=raw.find(b'\0')
            need(0<end<=limits.max_symbol_bytes,'callee_symbol_extent')
            try: name=raw[:end].decode('ascii')
            except UnicodeDecodeError: raise _Stop('callee_symbol_encoding')
            aliases.append(name)
            symbol_records.append(dict(n_type=kind,n_sect=section_index,n_desc=desc,
                slice_file_offset=offset+16*i,container_file_offset=image.slice_offset+offset+16*i))
        need(len(aliases)==1,'callee_aliases' if aliases else 'callee_symbols_missing')
        from .swift_declaration_profiles import parse_broad_declaration, ParseLimits, CallableKind
        charge(len(aliases[0]))
        parsed=parse_broad_declaration(aliases[0],limits=ParseLimits(max_symbol_length=limits.max_symbol_bytes))
        local=symbol_records[0]['n_type']==14
        private=symbol_records[0]['n_type']==30
        private_weak=private and symbol_records[0]['n_desc']==0x80
        # A direct BL names the concrete implementation entry, even when the
        # class also has a separate dynamic dispatch thunk. This grants syntax
        # only; static spelling does not establish dispatch or ABI authority.
        private_static=(private and symbol_records[0]['n_desc']==0 and parsed.supported
             and parsed.identity.callable_kind==CallableKind.STATIC_METHOD
             and parsed.identity.throws and bool(parsed.identity.context)
             and parsed.identity.context[-1].kind=='class'
             and parsed.identity.specialization is None)
        specialization=(parsed.identity.specialization if parsed.supported else None)
        need(not (local or private) or private_static or (parsed.supported and
             (local or private_weak) and
             parsed.identity.callable_kind==CallableKind.GENERIC_SPECIALIZATION and
             specialization is not None and bool(specialization.bindings)),'callee_visibility')
        result['symbol_evidence']={**symbol_records[0],
            'visibility':('private_extern_throwing_class_static_body' if private_static
                          else 'private_extern_weak_concrete_specialization' if private_weak
                          else 'local_concrete_specialization' if local else 'public'),
            'private_extern_static_body':private_static,
            'private_extern_weak_specialization':private_weak,
            'local_specialization':local,
            'specialization_kind':specialization.kind.value if specialization is not None else None}
        result['declaration']=dict(status='syntax_admitted' if parsed.supported else 'syntax_unresolved',
            identity=asdict(parsed.identity) if parsed.supported else None,
            reason=None if parsed.supported else parsed.unsupported_reason.value)
        result.update(status='tail_call_candidate' if tail else 'admitted_callsite',reason='exact_local_constant_target' if indirect else 'exact_local_direct_target',
                      syntactic_call_target_admitted=True,symbol=aliases[0])
        if session is None:
            charge(len(image.functions)+len(image.sections))
            result['binding']=dict(image=_identity(image),functions=[asdict(f) for f in image.functions],
                                   sections=[asdict(s) for s in image.sections],reads=reads)
        else:
            result['binding']=dict(image=_identity(image),session_required=True,reads=reads)
            result['session_initial_work_steps']=session.initial_work_steps
    except _Stop as exc:
        result.update(status='unresolved' if exc.incomplete or exc.reason.startswith('indirect_') else 'declined',
                      reason=exc.reason,details_complete=not exc.incomplete,
                      syntactic_call_target_admitted=False)
    result['work_steps']=work
    return result


_MINT = object()


class CallsiteSessionError(ValueError):
    def __init__(self,reason,work_steps):
        super().__init__(reason);self.reason=reason;self.work_steps=work_steps


@dataclass(frozen=True,slots=True,init=False)
class CallsiteSession:
    _seal: object
    _image: object
    _data: bytes
    _sections: tuple
    _functions: tuple
    _identity_fields: tuple
    _table: tuple
    _symbol_index: object
    _entry_values: tuple
    _function_index: object
    _raw_reads: tuple
    _record_count: int
    initial_work_steps: int
    _limits: CallsiteLimits


def _session_matches(image,session):
    return (type(session) is CallsiteSession and getattr(session,'_seal',None) is _MINT
        and image is session._image and image.data is session._data
        and image.sections is session._sections and image.functions is session._functions
        and tuple(_identity(image).items())==session._identity_fields)


def create_callsite_session(image, *, limits=CallsiteLimits()):
    """Parse invariant raw metadata once for this exact immutable image object."""
    work=0;reads=[]
    def need(ok,reason,incomplete=False):
        if not ok: raise _Stop(reason,incomplete)
    def charge(n=1):
        nonlocal work
        need(n<=limits.max_work-work,'callsite_work_limit',True);work+=n
    def read(offset,size):
        charge(size+1)
        need(0<=offset and 0<=size and offset+size<=len(image.data)
             and offset+size<=image.slice_size,'selected_slice_mapping')
        raw=image.data[offset:offset+size];reads.append((offset,raw));return raw
    def unpack(fmt,offset):return struct.unpack(fmt,read(offset,struct.calcsize(fmt)))
    try:
        _bound_metadata(image,limits,need,charge)
        table=_parse_raw_metadata(image,limits,need,charge,read,unpack)
        offset,count,_,_=table;index={};entries=[];functions={}
        for i in range(count):
            charge();row=unpack('<IBBHQ',offset+16*i)
            index.setdefault(row[4],[]).append((i,row))
            if not row[1]&0xe0:entries.append(row[4])
        charge(len(entries)*max(1,len(entries).bit_length()))
        entries.sort()
        for function in image.functions:
            charge();need(function.start not in functions,'callee_overlap')
            functions[function.start]=function
        charge(len(index)+count+len(reads)+len(CallsiteSession.__dataclass_fields__))
        frozen_index=MappingProxyType({pc:tuple(rows) for pc,rows in index.items()})
        return _mint_frozen(CallsiteSession,_MINT,image,image.data,image.sections,image.functions,
            tuple(_identity(image).items()),table,frozen_index,tuple(entries),
            MappingProxyType(functions),tuple(reads),max(len(image.functions),len(image.sections),count),work,limits)
    except _Stop as exc:raise CallsiteSessionError(exc.reason,work) from exc


class _FrozenList(tuple):
    pass


def _freeze_record(value):
    if type(value) is dict:return MappingProxyType({k:_freeze_record(v) for k,v in value.items()})
    if type(value) is list:return _FrozenList(_freeze_record(v) for v in value)
    if type(value) is tuple:return tuple(_freeze_record(v) for v in value)
    return value


def _thaw_record(value):
    if isinstance(value,MappingProxyType):return {k:_thaw_record(v) for k,v in value.items()}
    if type(value) is _FrozenList:return [_thaw_record(v) for v in value]
    if type(value) is tuple:return tuple(_thaw_record(v) for v in value)
    return value


@dataclass(frozen=True,slots=True,init=False)
class _CallsiteCapability:
    _seal: object
    _session: CallsiteSession
    _record: object
    _copy_work: int

    def record(self):return _thaw_record(self._record)


def _mint_frozen(cls,*values):
    # Public constructors and dataclasses.replace cannot inherit factory custody.
    instance=object.__new__(cls)
    for field,value in zip(cls.__dataclass_fields__,values):object.__setattr__(instance,field,value)
    return instance


def _copy_cost(value,max_work):
    work=0;pending=[value]
    while pending:
        work+=1
        if work>max_work:return None
        item=pending.pop()
        if isinstance(item,str):work+=len(item)
        elif isinstance(item,(dict,MappingProxyType)):
            work+=len(item)
            if work>max_work:return None
            pending.extend(item.values())
        elif isinstance(item,(tuple,list)):
            work+=len(item)
            if work>max_work:return None
            pending.extend(item)
    return work if work<=max_work else None


def admit_callsite_capability(image,caller,call_pc,*,limits=CallsiteLimits(),abi_profile=None,session=None):
    """Mint process-local custody; `.record()` is a copy, never reusable authority."""
    initial=0
    if session is None:
        session=create_callsite_session(image,limits=limits);initial=session.initial_work_steps
    record=admit_broad_swift_callsite(image,caller,call_pc,limits=limits,
                                    abi_profile=abi_profile,session=session)
    cost=_copy_cost(record,max(0,(limits.max_work-record['work_steps']-8)//2))
    if cost is None:raise CallsiteSessionError('callsite_capability_copy_limit',record['work_steps'])
    record['work_steps']+=2*cost+8+initial
    return _mint_frozen(_CallsiteCapability,_MINT,session,_freeze_record(record),cost)


def validate_callsite_capability(image,capability,*,max_work=100000):
    """Check private custody and per-call bytes; report incremental check work."""
    if (type(max_work) is not int or max_work<1 or type(capability) is not _CallsiteCapability
        or getattr(capability,'_seal',None) is not _MINT or not _session_matches(image,capability._session)):
        return None
    record=capability._record
    if record.get('status')!='admitted_callsite' or not record.get('syntactic_call_target_admitted'):
        return None
    work=1+capability._copy_work
    if work>max_work:return None
    for offset,raw in record['binding']['reads']:
        work+=1+len(raw)//2
        if work>max_work:return None
        expected=bytes.fromhex(raw)
        if image.data[offset:offset+len(expected)]!=expected:return None
    output=capability.record()
    output['admission_work_steps']=output['work_steps']
    output['work_steps']=work
    return output
