#!/usr/bin/env python3
"""
RISC-V Decoder Header Generator
Generate RISC-V decoder header directly from riscv-opcodes
"""

import sys
import re

instructions = []
instruction_info = {}  # name -> {category, has_load, has_store, etc.}

def parse_opcodes(input_file):
    """Parse riscv-opcodes file"""
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Skip lines starting with $ (keywords like $pseudo_op, $import)
            if line.startswith('$'):
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
            
            name = parts[0]
            instructions.append(name)
            
            # Store instruction info for later use
            category = classify_instruction(name)
            instruction_info[name] = {
                'category': category,
                'is_load': category == 'load',
                'is_store': category == 'store',
                'is_branch': category == 'branch',
                'is_jump': category == 'jump',
                'is_atomic': category == 'atomic',
                'is_fence': category == 'fence',
                'is_muldiv': category == 'muldiv',
                'is_float': category == 'float',
                'is_vector': category == 'vector',
            }

def classify_instruction(name):
    """Classify instruction by type"""
    if name.startswith(('beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu', 'c.beqz', 'c.bnez')):
        return 'branch'
    elif name.startswith(('jal', 'jalr', 'c.j', 'c.jal')):
        return 'jump'
    # Load instructions (scalar + vector)
    elif name.startswith(('lb', 'lh', 'lw', 'ld', 'lbu', 'lhu', 'lwu', 'flw', 'fld', 
                          'c.lw', 'c.ld', 'c.lwsp', 'c.ldsp', 'c.flw', 'c.fld', 'c.flwsp', 'c.fldsp',
                          'vle', 'vlse', 'vluxei', 'vloxei', 'vl1re', 'vl2re', 'vl4re', 'vl8re',
                          'vlm.v', 'vle8.v', 'vle16.v', 'vle32.v', 'vle64.v')):
        return 'load'
    # Store instructions (scalar + vector)
    elif name.startswith(('sb', 'sh', 'sw', 'sd', 'fsw', 'fsd', 
                          'c.sw', 'c.sd', 'c.swsp', 'c.sdsp', 'c.fsw', 'c.fsd', 'c.fswsp', 'c.fsdsp',
                          'vsuxei', 'vsoxei', 'vsse',
                          'vsm.v', 'vse8.v', 'vse16.v', 'vse32.v', 'vse64.v')) and not name.startswith('vset'):
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

def generate_header():
    """Generate header file"""
    print("/* Generated from riscv-opcodes */")
    print("/* RISC-V Decoder Header - rv8-independent version */")
    print()
    print("#ifndef RISCV_DECODER_GENERATED_H")
    print("#define RISCV_DECODER_GENERATED_H")
    print()
    print("#include <cstdint>")
    print("#include <cstring>")
    print()
    print("namespace riscv {")
    print()
    
    # Basic type definitions
    print("/* Basic types */")
    print("typedef uint64_t inst_t;")
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
        category = classify_instruction(name)
        print(f"    rv_op_{name.replace('.', '_')} = {i},  /* {category} */")
    print("};")
    print()
    
    # Instruction name array
    print("/* Instruction name strings */")
    print("static const char* rv_inst_name_sym[] = {")
    print('    "illegal",')
    for name in instructions:
        print(f'    "{name}",')
    print("};")
    print()
    
    # Instruction classification arrays
    print("/* Instruction classification */")
    print("static const bool rv_inst_is_load[] = {")
    print("    false, /* illegal */")
    for name in instructions:
        print(f"    {'true' if instruction_info[name]['is_load'] else 'false'},  /* {name} */")
    print("};")
    print()
    
    print("static const bool rv_inst_is_store[] = {")
    print("    false, /* illegal */")
    for name in instructions:
        print(f"    {'true' if instruction_info[name]['is_store'] else 'false'},  /* {name} */")
    print("};")
    print()
    
    print("static const bool rv_inst_is_branch[] = {")
    print("    false, /* illegal */")
    for name in instructions:
        print(f"    {'true' if instruction_info[name]['is_branch'] else 'false'},  /* {name} */")
    print("};")
    print()
    
    print("static const bool rv_inst_is_atomic[] = {")
    print("    false, /* illegal */")
    for name in instructions:
        print(f"    {'true' if instruction_info[name]['is_atomic'] else 'false'},  /* {name} */")
    print("};")
    print()
    
    print("static const bool rv_inst_is_fence[] = {")
    print("    false, /* illegal */")
    for name in instructions:
        print(f"    {'true' if instruction_info[name]['is_fence'] else 'false'},  /* {name} */")
    print("};")
    print()
    
    # Simple decoder functions
    print("/* Simple instruction length check */")
    print("inline int inst_length(inst_t inst) {")
    print("    return ((inst & 0x3) != 0x3) ? 2 : 4;")
    print("}")
    print()
    
    print("/* Decode instruction opcode (simplified) */")
    print("inline int decode_inst_op(uint32_t inst) {")
    print("    // Simplified implementation: full decoding requires additional logic")
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
    if len(sys.argv) < 2:
        print("Usage: generate_decoder.py <opcodes_file>", file=sys.stderr)
        sys.exit(1)
    
    parse_opcodes(sys.argv[1])
    generate_header()

if __name__ == "__main__":
    main()

