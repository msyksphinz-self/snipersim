#!/usr/bin/env python3
"""
riscv-opcodes形式からrv8メタデータ形式への変換スクリプト

使用方法:
  python3 riscv_opcodes_to_rv8.py < riscv-opcodes/opcodes > rv8/meta/opcodes
"""

import sys
import re

# オペランド位置定義（parse-opcodesから）
arglut = {
    'rd': (11, 7),
    'rs1': (19, 15),
    'rs2': (24, 20),
    'rs3': (31, 27),
    'aqrl': (26, 25),
    'pred': (27, 24),
    'succ': (23, 20),
    'rm': (14, 12),
    'imm20': (31, 12),
    'jimm20': (31, 12),
    'imm12': (31, 20),
    'imm12hi': (31, 25),
    'bimm12hi': (31, 25),
    'imm12lo': (11, 7),
    'bimm12lo': (11, 7),
    'zimm': (19, 15),
    'shamt': (25, 20),
    'shamtw': (24, 20),
}

# codec推論ルール
def infer_codec(name, args):
    """命令名とオペランドからcodecを推論"""
    args_set = set(args)
    
    # Compressed instructions
    if name.startswith('c.'):
        if 'crs1rdq' in args or 'crdq' in args:
            return 'cl' if any(a.startswith('cimm') for a in args) else 'cs'
        return 'c'
    
    # Fence instructions
    if 'pred' in args_set and 'succ' in args_set:
        return 'r·f'
    
    # Atomic instructions
    if 'aq' in args_set or 'rl' in args_set or 'aqrl' in args_set:
        if 'rs2' in args_set:
            return 'r·a'
        else:
            return 'r·l'
    
    # CSR instructions
    if any('csr' in arg for arg in args):
        if 'zimm' in args_set:
            return 'i·csr+i'
        else:
            return 'i·csr'
    
    # R4-type (fused multiply-add)
    if 'rs3' in args_set or 'frs3' in args_set:
        if 'rm' in args_set:
            return 'r4·m'
        return 'r4'
    
    # Floating-point with rounding mode
    if 'rm' in args_set:
        has_frd = 'frd' in args_set
        has_frs1 = 'frs1' in args_set
        has_frs2 = 'frs2' in args_set
        has_rd = 'rd' in args_set
        has_rs1 = 'rs1' in args_set
        
        if has_frs1 and has_frs2:
            return 'r·m+3f'
        elif has_frd and has_frs1:
            return 'r·m+ff'
        elif has_frd and has_rs1:
            return 'r·m+fr'
        elif has_rd and has_frs1:
            return 'r·m+rf'
        return 'r·m'
    
    # R-type variations
    if 'rd' in args_set and 'rs1' in args_set and 'rs2' in args_set:
        return 'r'
    if 'frd' in args_set and 'frs1' in args_set and 'frs2' in args_set:
        return 'r+3f'
    if 'frd' in args_set and 'rs1' in args_set:
        return 'r+fr'
    if 'rd' in args_set and 'frs1' in args_set:
        if 'frs2' in args_set:
            return 'r+rff'
        return 'r+rf'
    
    # I-type variations
    if 'rd' in args_set and 'rs1' in args_set:
        if 'shamt' in args_set or 'shamtw' in args_set:
            # Shift instructions
            if 'shamtw' in args_set:
                return 'i·sh5'  # RV64 word shifts
            elif any('31..26=' in str(token) or '31..25=' in str(token) for token in args):
                return 'i·sh6'
            return 'i·sh5'
        if 'imm12' in args_set:
            return 'i'
        if 'oimm12' in args_set:
            return 'i+o'
    
    # Load instructions
    if 'frd' in args_set and 'rs1' in args_set and 'oimm12' in args_set:
        return 'i+lf'
    if 'rd' in args_set and 'rs1' in args_set and 'oimm12' in args_set:
        return 'i+l'
    
    # S-type (store)
    if 'rs1' in args_set and 'rs2' in args_set and ('imm12hi' in args_set or 'simm12' in args_set):
        return 's'
    if 'rs1' in args_set and 'frs2' in args_set and 'simm12' in args_set:
        return 's+f'
    
    # SB-type (branch)
    if 'rs1' in args_set and 'rs2' in args_set and ('bimm12hi' in args_set or 'sbimm12' in args_set):
        return 'sb'
    
    # U-type
    if 'rd' in args_set and 'imm20' in args_set:
        return 'u'
    if 'rd' in args_set and 'oimm20' in args_set:
        return 'u+o'
    
    # UJ-type (jump)
    if 'rd' in args_set and 'jimm20' in args_set:
        return 'uj'
    
    return 'unknown'

# 拡張推論ルール
def infer_extensions(name, opcode_str, comment):
    """命令名、オペコード文字列、コメントから拡張を推論"""
    
    # コメントから拡張を検出
    ext_char = ''
    if comment:
        comment_lower = comment.lower()
        if 'rv32m' in comment_lower or 'rv64m' in comment_lower:
            ext_char = 'm'
        elif 'rv32a' in comment_lower or 'rv64a' in comment_lower:
            ext_char = 'a'
        elif 'rv32f' in comment_lower or 'rv64f' in comment_lower:
            ext_char = 'f'
        elif 'rv32d' in comment_lower or 'rv64d' in comment_lower:
            ext_char = 'd'
        elif 'rv32q' in comment_lower or 'rv64q' in comment_lower:
            ext_char = 'q'
        elif 'rv32c' in comment_lower or 'rv64c' in comment_lower:
            ext_char = 'c'
        elif 'rv32s' in comment_lower or 'rv64s' in comment_lower:
            ext_char = 's'
    
    # 命令名から推論
    if not ext_char:
        if name.startswith('c.'):
            ext_char = 'c'
        elif any(name.startswith(p) for p in ['amo', 'lr.', 'sc.']):
            ext_char = 'a'
        elif name.startswith('mul') or name.startswith('div') or name.startswith('rem'):
            ext_char = 'm'
        elif '.s' in name or name.startswith('f') and '.s' in name:
            ext_char = 'f'
        elif '.d' in name or name.startswith('f') and '.d' in name:
            ext_char = 'd'
        elif '.q' in name or name.startswith('f') and '.q' in name:
            ext_char = 'q'
        elif any(name.startswith(p) for p in ['sret', 'mret', 'wfi', 'sfence']):
            ext_char = 's'
        else:
            ext_char = 'i'
    
    # RV32/RV64/RV128の判定
    rv_widths = []
    
    # RV64専用命令
    rv64_only_names = ['ld', 'lwu', 'sd', 'addiw', 'slliw', 'srliw', 'sraiw', 'addw', 'subw', 'sllw', 'srlw', 'sraw', 'mulw', 'divw', 'divuw', 'remw', 'remuw']
    # 'w'で終わっても32ビットにも存在する命令（lw, sw等）
    rv32_also_w = ['lw', 'sw', 'flw', 'fsw']
    
    if (name in rv64_only_names or (name.endswith('w') and name not in rv32_also_w) or '.l' in name or '.lu' in name):
        if 'rv64' in comment.lower() or name in rv64_only_names:
            rv_widths = ['rv64' + ext_char, 'rv128' + ext_char]
        elif name.endswith('w'):
            # RV64W instructions
            rv_widths = ['rv64' + ext_char, 'rv128' + ext_char]
        else:
            rv_widths = ['rv32' + ext_char, 'rv64' + ext_char, 'rv128' + ext_char]
    # RV128専用命令
    elif '.t' in name or '.tu' in name:
        rv_widths = ['rv128' + ext_char]
    else:
        rv_widths = ['rv32' + ext_char, 'rv64' + ext_char, 'rv128' + ext_char]
    
    return ' '.join(rv_widths)

# rv8形式のオペランド名変換
def convert_operand_name(arg):
    """riscv-opcodesのオペランド名をrv8形式に変換"""
    conversions = {
        'imm12': 'imm12',
        'imm12hi': 'simm12',  # Store用
        'imm12lo': '',  # Store用（統合される）
        'bimm12hi': 'sbimm12',  # Branch用
        'bimm12lo': '',  # Branch用（統合される）
        'jimm20': 'jimm20',
        'imm20': 'imm20',
        'shamt': 'shamt5',
        'shamtw': 'shamt5',
    }
    return conversions.get(arg, arg)

def normalize_operands(args):
    """オペランドリストを正規化してrv8形式の順序に並べ替え"""
    # bimm12hi/bimm12lo -> sbimm12 (branch用)
    if 'bimm12hi' in args and 'bimm12lo' in args:
        # rv8形式: rs1 rs2 sbimm12
        result = []
        if 'rs1' in args:
            result.append('rs1')
        if 'rs2' in args:
            result.append('rs2')
        result.append('sbimm12')
        return result
    
    # imm12hi/imm12lo -> simm12 (store用)
    if 'imm12hi' in args and 'imm12lo' in args:
        # rv8形式: rs1 rs2 simm12
        result = []
        if 'rs1' in args:
            result.append('rs1')
        if 'rs2' in args:
            result.append('rs2')
        if 'frs2' in args:
            result.append('frs2')
        result.append('simm12')
        return result
    
    # jimm20の場合 (jump用)
    if 'jimm20' in args:
        # rv8形式: rd jimm20
        result = []
        if 'rd' in args:
            result.append('rd')
        result.append('jimm20')
        return result
    
    # imm20の場合 (upper immediate用)
    if 'imm20' in args:
        # rv8形式: rd imm20 または rd oimm20
        result = []
        if 'rd' in args:
            result.append('rd')
        # auipc命令の場合はoimm20
        result.append('imm20')  # 後でauipcの場合はoimm20に変換
        return result
    
    # R-type (rd rs1 rs2) - rs2があるかチェックして優先
    if 'rd' in args and 'rs1' in args and 'rs2' in args:
        result = ['rd', 'rs1', 'rs2']
        if 'rm' in args:
            result.append('rm')
        if 'rs3' in args or 'frs3' in args:
            result.insert(3, 'frs3' if 'frs3' in args else 'rs3')
        return result
    
    # Float R-type variations
    if 'frd' in args and 'frs1' in args and 'frs2' in args:
        result = ['frd', 'frs1', 'frs2']
        if 'rm' in args:
            result.append('rm')
        if 'frs3' in args:
            result.insert(3, 'frs3')
        return result
    
    if 'frd' in args and 'frs1' in args:
        result = ['frd', 'frs1']
        if 'rm' in args:
            result.append('rm')
        return result
    
    if 'rd' in args and 'frs1' in args:
        result = ['rd', 'frs1']
        if 'frs2' in args:
            result.append('frs2')
        if 'rm' in args:
            result.append('rm')
        return result
    
    if 'frd' in args and 'rs1' in args:
        result = ['frd', 'rs1']
        if 'rm' in args:
            result.append('rm')
        return result
    
    # Atomic instructions
    if 'aq' in args or 'rl' in args or 'aqrl' in args:
        result = []
        if 'rd' in args:
            result.append('rd')
        if 'rs1' in args:
            result.append('rs1')
        if 'rs2' in args:
            result.append('rs2')
        if 'aqrl' in args:
            result.append('aqrl')
        elif 'aq' in args or 'rl' in args:
            if 'aq' in args:
                result.append('aq')
            if 'rl' in args:
                result.append('rl')
        return result
    
    # Fence instructions
    if 'pred' in args and 'succ' in args:
        return ['pred', 'succ']
    
    # CSR instructions
    if any('csr' in str(a) for a in args):
        result = []
        if 'rd' in args:
            result.append('rd')
        if 'rs1' in args:
            result.append('rs1')
        elif 'zimm' in args:
            result.append('zimm')
        # CSR番号は暗黙的
        return result
    
    # Load命令の場合 (rd rs1 imm12) - opcodeで判定
    # Load opcodes: 0x00, jalr: 0x19
    # 注: 後でopcode情報から判定できるように変更可能
    
    # その他のI-type (rd rs1 imm12/shamt)
    if 'rd' in args and 'rs1' in args:
        result = ['rd', 'rs1']
        if 'imm12' in args:
            # デフォルトはimm12だが、load/jalr/auipcの場合はoimm12
            result.append('imm12')
        elif 'shamt' in args:
            result.append('shamt5')
        elif 'shamtw' in args:
            result.append('shamt5')
        return result
    
    # Float load命令の場合 (frd rs1 imm12)
    if 'frd' in args and 'rs1' in args and 'imm12' in args:
        return ['frd', 'rs1', 'oimm12']
    
    # Fallback: convert in place
    return [convert_operand_name(a) for a in args]

def main():
    print("# format of a line in this file:")
    print("# <instruction name> [<args> ...] <opcode> <codec> <extension>")
    print("#")
    print("# <args> is one of rd, rs1, rs2, frd, frs1, frs2, frs3, imm20, imm12,")
    print("# sbimm12, simm12, shamt5, shamt6, rm, aq, rl, pred, succ")
    print("#")
    print("# <opcode> is given by specifying one or more range/value pairs:")
    print("# hi..lo=value or bit=value or arg=value (e.g. 6..2=0x45 10=1)")
    print("#")
    print("# <codec> is one of r, i, s, sb, u, uj, ...")
    print("#")
    print("# <extension> is one of { rv32, rv64, rv128 } · { i, m, a, f, d, s, c }")
    print()
    
    current_section = ""
    
    for line in sys.stdin:
        # コメント処理
        parts = line.partition('#')
        code_part = parts[0]
        comment = parts[2].strip() if parts[1] else ""
        
        tokens = code_part.split()
        
        # 空行またはコメント行
        if len(tokens) == 0:
            if comment:
                # セクションコメント
                if comment.startswith('RV'):
                    current_section = comment
                    print()
                    print(f"# {comment}")
                    print()
            continue
        
        if len(tokens) < 2:
            continue
        
        name = tokens[0]
        
        # 疑似命令のスキップ
        if name.startswith('@'):
            continue
        
        # オペランドとエンコーディングを分離
        operands = []
        encoding = []
        
        for token in tokens[1:]:
            if '=' in token or '..' in token:
                encoding.append(token)
            elif token in arglut:
                operands.append(token)
        
        # オペランドを正規化
        normalized_ops = normalize_operands(operands)
        
        # Codecを推論
        codec = infer_codec(name, operands + encoding)
        
        # Load命令のcodecをi+lに修正（floadはi+lf）
        for enc in encoding:
            if '6..2=0x00' in enc:  # Load opcode
                if 'frd' in operands:
                    codec = 'i+lf'
                else:
                    codec = 'i+l'
                break
            elif '6..2=0x01' in enc and 'frd' in operands:  # FP load
                codec = 'i+lf'
                break
            elif '6..2=0x08' in enc:  # Store opcode
                if 'frs2' in operands:
                    codec = 's+f'
                # sはすでに正しい
                break
            elif '6..2=0x09' in enc and 'frs2' in operands:  # FP store
                codec = 's+f'
                break
        
        # 拡張を推論
        extensions = infer_extensions(name, ' '.join(encoding), comment or current_section)
        
        # rv8形式で出力
        # 命令名を左寄せ（10文字幅）
        output = f"{name:<10}"
        
        # オペランドを後処理: load/jalr/auipcの場合はimm12をoimm12に変換
        final_ops = []
        for op in normalized_ops:
            if op == 'imm12':
                # Load命令 (opcode 0x00), jalr (opcode 0x19) の場合はoimm12
                is_load_or_jalr = False
                for enc in encoding:
                    if '6..2=0x00' in enc or '6..2=0x19' in enc:
                        is_load_or_jalr = True
                        break
                if is_load_or_jalr:
                    final_ops.append('oimm12')
                else:
                    final_ops.append(op)
            else:
                final_ops.append(op)
        
        # auipcの場合はimm20をoimm20に変換
        if name == 'auipc':
            final_ops = ['rd', 'oimm20'] if 'rd' in final_ops and 'imm20' in final_ops else final_ops
        
        # オペランドを出力（30文字幅）
        ops_str = ' '.join(final_ops)
        output += f" {ops_str:<30}"
        
        # エンコーディングを出力
        enc_str = ' '.join(encoding)
        output += f" {enc_str:<40}"
        
        # Codecを出力（6文字幅）
        output += f" {codec:<6}"
        
        # 拡張を出力
        output += f" {extensions}"
        
        print(output)

if __name__ == '__main__':
    main()

