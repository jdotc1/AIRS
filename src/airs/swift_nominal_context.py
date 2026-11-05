"""Bounded direct Swift struct-context records; never loads runtime metadata."""
import struct
from .types import InputError

def admit_struct_context(image, declaration, *, max_entries=1024, charge=None):
    """Match a unique direct __swift5_types descriptor with struct -> module parents."""
    if charge is None:
        charge = lambda: None
    result = {'status': 'declined', 'reason': 'method_context_not_admitted'}
    section = image.section('__TEXT', '__swift5_types')
    if section is None or section.size % 4 or section.size // 4 > max_entries:
        return result
    def word(pc):
        charge()
        return struct.unpack('<I', image.bytes_at(pc, 4))[0]
    def relative(pc):
        charge()
        offset = struct.unpack('<i', image.bytes_at(pc, 4))[0]
        if offset == 0:
            raise ValueError('null relative pointer')
        target = pc + offset
        if not 0 <= target < 1 << 64:
            raise ValueError('relative overflow')
        return target
    def string(pc):
        data = bytearray()
        for offset in range(129):
            charge()
            b = image.bytes_at(pc + offset, 1)[0]
            if b == 0:
                return data.decode('ascii')
            data.append(b)
        raise ValueError('oversized identifier')
    matches = []
    try:
        for offset in range(0, section.size, 4):
            field = section.address + offset
            # Low-bit tagged indirect entries are outside this model.
            if word(field) & 1:
                return result
            descriptor = relative(field)
            flags = word(descriptor)
            if flags & 31 != 17:
                continue
            owner = string(relative(descriptor + 8))
            if owner != declaration.type_name:
                continue
            parent = relative(descriptor + 4)
            parent_flags = word(parent)
            module = string(relative(parent + 8))
            if module != declaration.module:
                continue
            # Generic flag, descriptor version, imported/special contexts decline.
            if flags != 0x51 or parent_flags not in (0, 0x40) or word(parent + 4) != 0:
                return result
            charge()
            image.bytes_at(descriptor, 28)
            matches.append({'descriptor_pc': hex(descriptor), 'descriptor_flags': hex(flags),
                            'parent_pc': hex(parent), 'parent_flags': hex(parent_flags),
                            'type_name': owner, 'module': module,
                            'raw_descriptor': image.bytes_at(descriptor, 28).hex(),
                            'raw_parent': image.bytes_at(parent, 12).hex()})
        if len(matches) == 1:
            return {'status': 'admitted_struct_context', **matches[0]}
    except (InputError, ValueError, UnicodeError, struct.error):
        pass
    return result
