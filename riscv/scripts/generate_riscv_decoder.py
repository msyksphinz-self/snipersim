#!/usr/bin/env python3
"""
Enhanced RISC-V Decoder Generator
Parse riscv-opcodes with arg_lut.csv for precise operand information
"""

import sys
import re
import csv
import os

instructions = []
instruction_info = {}
arg_lut = {}
instruction_encodings = {}  # Store encoding match/mask for each instruction

def load_arg_lut(arg_lut_file):
    """Load argument lookup table"""
    global arg_lut
    with open(arg_lut_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                name = row[0].strip('"')
                hi = int(row[1].strip())
                lo = int(row[2].strip())
                arg_lut[name] = (hi, lo)

def determine_operand_type(arg_name):
    """Determine operand type from argument name"""
    # Integer registers
    if arg_name in ['rd', 'rs1', 'rs2', 'rs3', 'rd_n0', 'rd_n2', 'rs1_n0', 
                    'rd_rs1', 'rd_rs1_n0', 'rd_rs1_p', 'rs1_p', 'rs2_p', 'rd_p']:
        return 'GPR'
    
    # Floating-point registers (not in current schema, but for future)
    if arg_name in ['frd', 'frs1', 'frs2', 'frs3']:
        return 'FPR'
    
    # Vector registers
    if arg_name in ['vd', 'vs1', 'vs2', 'vs3']:
        return 'VPR'
    
    # Compressed registers
    if 'c_' in arg_name and ('rs1' in arg_name or 'rs2' in arg_name or 'rd' in arg_name):
        return 'GPR'
    
    # Immediates
    if 'imm' in arg_name or 'zimm' in arg_name or 'simm' in arg_name:
        return 'IMM'
    
    # Special fields
    if arg_name in ['rm', 'aq', 'rl', 'aqrl', 'vm', 'wd', 'nf']:
        return 'FIELD'
    
    return 'UNKNOWN'

def get_memory_size(name):
    """Determine memory access size from instruction name"""
    if name.endswith(('b', 'lb', 'lbu', 'sb')):
        return 1
    elif name.endswith(('h', 'lh', 'lhu', 'sh')):
        return 2
    elif name.endswith(('w', 'lw', 'lwu', 'sw', 'flw', 'fsw')):
        return 4
    elif name.endswith(('d', 'ld', 'sd', 'fld', 'fsd')):
        return 8
    elif name.endswith(('q', 'lq', 'sq')):
        return 16
    # Vector loads/stores - element width
    elif 'vle8' in name or 'vse8' in name:
        return 1
    elif 'vle16' in name or 'vse16' in name:
        return 2
    elif 'vle32' in name or 'vse32' in name:
        return 4
    elif 'vle64' in name or 'vse64' in name:
        return 8
    return 0

def parse_encoding_fields(parts):
    """Parse encoding fields (e.g., '6..2=0x0D', '1..0=3') and return match/mask"""
    match_bits = ['-'] * 32
    mask_bits = ['0'] * 32
    
    # Pattern for range assignments: msb..lsb=value
    range_pattern = re.compile(r'(\d+)\.\.(\d+)=([0-9xa-fA-F]+)')
    # Pattern for single bit assignments: bit=value (but not part of range)
    single_pattern = re.compile(r'^(\d+)=([0-9xa-fA-F]+)$')
    
    for part in parts:
        # Check for range assignment (e.g., "6..2=0x0D" or "31..25=0")
        range_match = range_pattern.search(part)
        if range_match:
            msb = int(range_match.group(1))
            lsb = int(range_match.group(2))
            value = int(range_match.group(3), 0)
            
            # Validate range
            if msb < lsb or msb >= 32 or lsb < 0:
                continue
            
            # Set bits in reverse order (bit 31 is MSB, stored at index 0)
            # For a range like 6..2, we extract bits from value starting at bit 0
            num_bits = msb - lsb + 1
            for i in range(num_bits):
                bit_pos = lsb + i
                bit_idx = 31 - bit_pos
                bit_val = (value >> i) & 1
                if bit_idx >= 0 and bit_idx < 32:
                    match_bits[bit_idx] = str(bit_val)
                    mask_bits[bit_idx] = '1'
            continue
        
        # Check for single bit assignment (e.g., standalone "1=3" - but this is rare)
        # Most single bits are part of ranges, so this might not match much
        single_match = single_pattern.match(part)
        if single_match:
            bit_pos = int(single_match.group(1))
            value = int(single_match.group(2), 0)
            
            if 0 <= bit_pos < 32:
                bit_idx = 31 - bit_pos
                match_bits[bit_idx] = str(value & 1)
                mask_bits[bit_idx] = '1'
    
    # Convert to integers
    # Replace '-' with '0' for match, keep mask as is
    match_str = ''.join(match_bits).replace('-', '0')
    mask_str = ''.join(mask_bits)
    
    try:
        match_val = int(match_str, 2) if match_str else 0
        mask_val = int(mask_str, 2) if mask_str else 0
        return match_val, mask_val
    except:
        return 0, 0

def parse_opcodes_enhanced(input_file):
    """Parse riscv-opcodes with operand analysis"""
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('$'):
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
            
            name = parts[0]
            instructions.append(name)
            
            # Parse operands
            operands = []
            encoding_parts = []
            found_encoding = False
            for i, part in enumerate(parts[1:]):
                # Check if this is an encoding field
                if '=' in part or '..' in part:
                    found_encoding = True
                    encoding_parts.append(part)
                elif not found_encoding:
                    # Stop at encoding fields (contain '=' or '..')
                    op_type = determine_operand_type(part)
                    if op_type != 'UNKNOWN':
                        operands.append({
                            'name': part,
                            'type': op_type,
                            'position': i
                        })
            
            # Parse encoding to get match/mask
            match_val, mask_val = parse_encoding_fields(encoding_parts)
            instruction_encodings[name] = {
                'match': match_val,
                'mask': mask_val
            }
            
            # Classify instruction
            category = classify_instruction(name)
            
            # Determine characteristics
            has_gpr = any(op['type'] == 'GPR' for op in operands)
            has_fpr = any(op['type'] == 'FPR' for op in operands)
            has_vpr = any(op['type'] == 'VPR' for op in operands)
            has_imm = any(op['type'] == 'IMM' for op in operands)
            
            instruction_info[name] = {
                'category': category,
                'operands': operands,
                'is_load': category == 'load',
                'is_store': category == 'store',
                'is_branch': category == 'branch',
                'is_jump': category == 'jump',
                'is_atomic': category == 'atomic',
                'is_fence': category == 'fence',
                'is_muldiv': category == 'muldiv',
                'is_float': category == 'float' or has_fpr,
                'is_vector': category == 'vector' or has_vpr,
                'has_gpr': has_gpr,
                'has_fpr': has_fpr,
                'has_vpr': has_vpr,
                'has_imm': has_imm,
                'mem_size': get_memory_size(name),
            }

def classify_instruction(name):
    """Classify instruction by type"""
    if name.startswith(('beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu', 'c.beqz', 'c.bnez')):
        return 'branch'
    elif name.startswith(('jal', 'jalr', 'c.j', 'c.jal')):
        return 'jump'
    elif name.startswith(('lb', 'lh', 'lw', 'ld', 'lbu', 'lhu', 'lwu', 'flw', 'fld', 
                          'c.lw', 'c.ld', 'c.lwsp', 'c.ldsp', 'c.flw', 'c.fld', 'c.flwsp', 'c.fldsp',
                          'vle', 'vlse', 'vluxei', 'vloxei', 'vl1re', 'vl2re', 'vl4re', 'vl8re',
                          'vlm.v', 'vle8', 'vle16', 'vle32', 'vle64')):
        return 'load'
    elif name.startswith(('sb', 'sh', 'sw', 'sd', 'fsw', 'fsd', 
                          'c.sw', 'c.sd', 'c.swsp', 'c.sdsp', 'c.fsw', 'c.fsd', 'c.fswsp', 'c.fsdsp',
                          'vsuxei', 'vsoxei', 'vsse',
                          'vsm.v', 'vse8', 'vse16', 'vse32', 'vse64')) and not name.startswith('vset'):
        return 'store'
    elif name.startswith(('lr.', 'sc.', 'amo')):
        return 'atomic'
    elif name.startswith(('mul', 'div', 'rem')):
        return 'muldiv'
    elif name.startswith(('fadd', 'fsub', 'fmul', 'fdiv', 'fmadd', 'fmsub', 'fnmadd', 'fnmsub', 'fmin', 'fmax', 'fsqrt', 'fld', 'fsd', 'flw', 'fsw', 'fcvt', 'fmv', 'feq', 'flt', 'fle', 'fclass', 'fsgnj')):
        return 'float'
    elif name.startswith(('fence', 'ecall', 'ebreak')):
        return 'fence'
    elif name.startswith(('andn', 'orn', 'xnor', 'clz', 'ctz', 'cpop', 'max', 'min', 'sext', 'zext', 'rol', 'ror', 'rev8', 'orc.b', 'bclr', 'bext', 'binv', 'bset', 'clmul', 'sh1add', 'sh2add', 'sh3add')):
        return 'bitmanip'
    elif name.startswith('c.'):
        return 'compressed'
    elif name.startswith('v'):
        return 'vector'
    else:
        return 'alu'

def generate_header_enhanced():
    """Generate enhanced header with operand information"""
    print("/* Generated from riscv-opcodes with enhanced operand analysis */")
    print("/* RISC-V Decoder Header - Enhanced Version */")
    print()
    print("#ifndef RISCV_DECODER_GENERATED_H")
    print("#define RISCV_DECODER_GENERATED_H")
    print()
    print("#include <cstdint>")
    print("#include <cstring>")
    print()
    print("namespace riscv {")
    print()
    
    # Basic types
    print("/* Basic types */")
    print("typedef uint64_t inst_t;")
    print()
    
    # Operand type enum
    print("/* Operand types */")
    print("enum rv_operand_type {")
    print("    RV_OP_NONE = 0,")
    print("    RV_OP_GPR,   // Integer register")
    print("    RV_OP_FPR,   // Float register")
    print("    RV_OP_VPR,   // Vector register")
    print("    RV_OP_IMM,   // Immediate")
    print("    RV_OP_FIELD, // Special field (rm, aq, rl, etc.)")
    print("};")
    print()
    
    # decode structure
    print("/* Decode structure */")
    print("struct decode {")
    print("    int32_t  imm;")
    print("    uint8_t  rd;")
    print("    uint8_t  rs1;")
    print("    uint8_t  rs2;")
    print("    uint8_t  rs3;")
    print("    uint16_t op    : 10;")
    print("    uint16_t codec : 6;")
    print("    uint8_t  rm    : 3;")
    print("    uint8_t  aq    : 1;")
    print("    uint8_t  rl    : 1;")
    print("    uint8_t  pred  : 4;")
    print("    uint8_t  succ  : 4;")
    print()
    print("    decode()")
    print("        : imm(0), rd(0), rs1(0), rs2(0), rs3(0), op(0), codec(0),")
    print("          rm(0), aq(0), rl(0), pred(0), succ(0) {}")
    print("};")
    print()
    
    # Instruction enum
    print(f"/* Instruction enum - {len(instructions)} instructions */")
    print("enum rv_op {")
    print("    rv_op_illegal = 0,")
    for i, name in enumerate(instructions, 1):
        category = instruction_info[name]['category']
        print(f"    rv_op_{name.replace('.', '_')} = {i},  /* {category} */")
    print("};")
    print()
    
    # Instruction names
    print("/* Instruction name strings */")
    print("static const char* rv_inst_name_sym[] = {")
    print('    "illegal",')
    for name in instructions:
        print(f'    "{name}",')
    print("};")
    print()
    
    # Classification arrays
    print("/* Instruction classification arrays */")
    
    classifications = [
        ('is_load', 'Load instructions'),
        ('is_store', 'Store instructions'),
        ('is_branch', 'Branch instructions'),
        ('is_atomic', 'Atomic instructions'),
        ('is_fence', 'Fence instructions'),
        ('is_float', 'Floating-point instructions'),
        ('is_vector', 'Vector instructions'),
    ]
    
    for field, comment in classifications:
        print(f"/* {comment} */")
        print(f"static const bool rv_inst_{field}[] = {{")
        print("    false, /* illegal */")
        for name in instructions:
            value = 'true' if instruction_info[name][field] else 'false'
            print(f"    {value},  /* {name} */")
        print("};")
        print()
    
    # Memory size array
    print("/* Memory access size (bytes, 0=no memory access) */")
    print("static const uint8_t rv_inst_mem_size[] = {")
    print("    0, /* illegal */")
    for name in instructions:
        mem_size = instruction_info[name]['mem_size']
        print(f"    {mem_size},  /* {name} */")
    print("};")
    print()
    
    # Operand type arrays
    print("/* Operand type information */")
    print("static const bool rv_inst_has_gpr[] = {")
    print("    false, /* illegal */")
    for name in instructions:
        value = 'true' if instruction_info[name]['has_gpr'] else 'false'
        print(f"    {value},  /* {name} */")
    print("};")
    print()
    
    print("static const bool rv_inst_has_fpr[] = {")
    print("    false, /* illegal */")
    for name in instructions:
        value = 'true' if instruction_info[name]['has_fpr'] else 'false'
        print(f"    {value},  /* {name} */")
    print("};")
    print()
    
    print("static const bool rv_inst_has_vpr[] = {")
    print("    false, /* illegal */")
    for name in instructions:
        value = 'true' if instruction_info[name]['has_vpr'] else 'false'
        print(f"    {value},  /* {name} */")
    print("};")
    print()
    
    # Simple decoder functions
    print("/* Simple instruction length check */")
    print("inline int inst_length(inst_t inst) {")
    print("    return ((inst & 0x3) != 0x3) ? 2 : 4;")
    print("}")
    print()
    
    # Generate decode table
    print("/* Instruction decoding table: (match, mask, opcode) */")
    print("struct decode_entry {")
    print("    uint32_t match;")
    print("    uint32_t mask;")
    print("    int opcode;")
    print("};")
    print()
    print("static const decode_entry decode_table[] = {")
    
    # Sort instructions by specificity (more specific masks first)
    sorted_instructions = sorted(instructions, key=lambda n: bin(instruction_encodings.get(n, {}).get('mask', 0)).count('1'), reverse=True)
    
    for name in sorted_instructions:
        if name in instruction_encodings:
            enc = instruction_encodings[name]
            opcode_idx = instructions.index(name) + 1  # +1 because rv_op_illegal = 0
            print(f"    {{0x{enc['match']:08x}, 0x{enc['mask']:08x}, rv_op_{name.replace('.', '_')}}},  /* {name} */")
    
    print("};")
    print()
    print("static const int decode_table_size = sizeof(decode_table) / sizeof(decode_table[0]);")
    print()
    
    print("/* Decode instruction opcode */")
    print("inline int decode_inst_op(uint32_t inst) {")
    print("    // Try to match instruction against decode table")
    print("    for (int i = 0; i < decode_table_size; i++) {")
    print("        if ((inst & decode_table[i].mask) == decode_table[i].match) {")
    print("            return decode_table[i].opcode;")
    print("        }")
    print("    }")
    print("    return rv_op_illegal;")
    print("}")
    print()
    
    print("/* Decode instruction fields (simplified) */")
    print("inline void decode_inst_rv64(decode &dec, inst_t inst) {")
    print("    uint32_t inst32 = inst & 0xFFFFFFFF;")
    print("    ")
    print("    // Extract basic fields")
    print("    dec.rd = (inst32 >> 7) & 0x1F;")
    print("    dec.rs1 = (inst32 >> 15) & 0x1F;")
    print("    dec.rs2 = (inst32 >> 20) & 0x1F;")
    print("    ")
    print("    // I-type immediate")
    print("    dec.imm = (int32_t)inst32 >> 20;")
    print("}")
    print()
    
    print("} // namespace riscv")
    print()
    print("#endif // RISCV_DECODER_GENERATED_H")

def main():
    """Main processing"""
    if len(sys.argv) < 3:
        print("Usage: generate_decoder_enhanced.py <arg_lut.csv> <opcodes_file>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  cat extensions/rv_i extensions/rv64_i | \\", file=sys.stderr)
        print("  python3 generate_decoder_enhanced.py arg_lut.csv /dev/stdin", file=sys.stderr)
        sys.exit(1)
    
    arg_lut_file = sys.argv[1]
    opcodes_file = sys.argv[2]
    
    # Load argument lookup table
    load_arg_lut(arg_lut_file)
    
    # Parse opcodes with operand analysis
    parse_opcodes_enhanced(opcodes_file)
    
    # Generate enhanced header
    generate_header_enhanced()

if __name__ == "__main__":
    main()

