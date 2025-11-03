#include "riscv_decoder_simple.h"
#include "riscv_decoder_generated.h"
#include <iostream>
#include <sstream>

using namespace riscv;

namespace dl 
{

const char* reg_name_sym[] = {
  "x0",  "x1",  "x2",  "x3",  "x4",  "x5",  "x6",  "x7",
  "x8",  "x9",  "x10", "x11", "x12", "x13", "x14", "x15",
  "x16", "x17", "x18", "x19", "x20", "x21", "x22", "x23",
  "x24", "x25", "x26", "x27", "x28", "x29", "x30", "x31",
  "f0",  "f1",  "f2",  "f3",  "f4",  "f5",  "f6",  "f7",
  "f8",  "f9",  "f10", "f11", "f12", "f13", "f14", "f15",
  "f16", "f17", "f18", "f19", "f20", "f21", "f22", "f23",
  "f24", "f25", "f26", "f27", "f28", "f29", "f30", "f31",
  "v0",  "v1",  "v2",  "v3",  "v4",  "v5",  "v6",  "v7",
  "v8",  "v9",  "v10", "v11", "v12", "v13", "v14", "v15",
  "v16", "v17", "v18", "v19", "v20", "v21", "v22", "v23",
  "v24", "v25", "v26", "v27", "v28", "v29", "v30", "v31",
  nullptr
};

// ========================================================================
// RISCVDecoderSimple
// ========================================================================

RISCVDecoderSimple::RISCVDecoderSimple(dl_arch arch, dl_mode mode, dl_syntax syntax)
{
  this->m_arch = arch;
  this->m_mode = mode;
  this->m_syntax = syntax;
  this->m_isa = DL_ISA_RISCV;
}

RISCVDecoderSimple::~RISCVDecoderSimple() {}

void RISCVDecoderSimple::decode(DecodedInst * inst)
{  
  riscv::decode dec;

  if(inst->get_already_decoded())
    return;

  riscv::inst_t r_inst;
  memcpy(&r_inst, inst->get_code(), 8);

  int op = riscv::decode_inst_op(r_inst);
  
  if (op == 0) {
    inst->get_size() = 4;
    inst->set_already_decoded(true);
    return;
  }
  
  uint32_t inst_bits = r_inst & 0xFFFFFFFF;
  inst->get_size() = ((inst_bits & 0x3) != 0x3) ? 2 : 4;

  riscv::decode_inst_rv64(dec, r_inst);
  ((RISCVDecodedInstSimple *)inst)->set_decode(dec);
  inst->set_already_decoded(true);
}

void RISCVDecoderSimple::decode(DecodedInst * inst, dl_isa isa) { this->decode(inst); }
void RISCVDecoderSimple::change_isa_mode(dl_isa new_isa) { this->m_isa = new_isa; }

const char* RISCVDecoderSimple::inst_name(unsigned int inst_id)
{
  if (inst_id > 0 && inst_id < sizeof(riscv::rv_inst_name_sym)/sizeof(riscv::rv_inst_name_sym[0])) {
    return riscv::rv_inst_name_sym[inst_id];
  }
  return "unknown";
}

const char* RISCVDecoderSimple::reg_name(unsigned int reg_id)
{
  if (reg_id < (unsigned int)dl::last_reg) return reg_name_sym[reg_id];
  return "unknown";
}

// Decoder仮想関数の実装（簡易版）
RISCVDecoderSimple::decoder_reg RISCVDecoderSimple::largest_enclosing_register(decoder_reg r) { return r; }
bool RISCVDecoderSimple::invalid_register(decoder_reg r) { return r >= (unsigned int)dl::last_reg; }
bool RISCVDecoderSimple::reg_is_program_counter(decoder_reg r) { return false; }
bool RISCVDecoderSimple::inst_in_group(const DecodedInst * inst, unsigned int group_id) { return false; }

unsigned int RISCVDecoderSimple::num_operands(const DecodedInst * inst)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  unsigned int count = 0;
  if (dec->rd != 0) count++;
  if (dec->rs1 != 0) count++;
  if (dec->rs2 != 0) count++;
  if (dec->imm != 0) count++;
  return count;
}

unsigned int RISCVDecoderSimple::num_memory_operands(const DecodedInst * inst)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  int op = dec->op;
  // Use generated classification arrays
  if (op > 0 && op < sizeof(riscv::rv_inst_is_load)/sizeof(riscv::rv_inst_is_load[0])) {
    if (riscv::rv_inst_is_load[op] || riscv::rv_inst_is_store[op]) {
      return 1;
    }
  }
  return 0;
}

RISCVDecoderSimple::decoder_reg RISCVDecoderSimple::mem_base_reg(const DecodedInst * inst, unsigned int mem_idx)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  return dec->rs1;
}

bool RISCVDecoderSimple::mem_base_upate(const DecodedInst* inst, unsigned int mem_idx) { return false; }
bool RISCVDecoderSimple::has_index_reg(const DecodedInst * inst, unsigned int mem_idx) { return false; }
RISCVDecoderSimple::decoder_reg RISCVDecoderSimple::mem_index_reg(const DecodedInst * inst, unsigned int mem_idx) { return 0; }

bool RISCVDecoderSimple::op_read_mem(const DecodedInst * inst, unsigned int mem_idx)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  int op = dec->op;
  // Use generated classification array
  if (op > 0 && op < sizeof(riscv::rv_inst_is_load)/sizeof(riscv::rv_inst_is_load[0])) {
    return riscv::rv_inst_is_load[op];
  }
  return false;
}

bool RISCVDecoderSimple::op_write_mem(const DecodedInst * inst, unsigned int mem_idx)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  int op = dec->op;
  // Use generated classification array
  if (op > 0 && op < sizeof(riscv::rv_inst_is_store)/sizeof(riscv::rv_inst_is_store[0])) {
    return riscv::rv_inst_is_store[op];
  }
  return false;
}

bool RISCVDecoderSimple::op_read_reg(const DecodedInst * inst, unsigned int idx)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  if (idx == 0 && dec->rs1 != 0) return true;
  if (idx == 1 && dec->rs2 != 0) return true;
  return false;
}

bool RISCVDecoderSimple::op_write_reg(const DecodedInst * inst, unsigned int idx)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  if (idx == 0 && dec->rd != 0) return true;
  return false;
}

bool RISCVDecoderSimple::is_addr_gen(const DecodedInst * inst, unsigned int idx) { return false; }
bool RISCVDecoderSimple::op_is_reg(const DecodedInst * inst, unsigned int idx) 
{ 
  return op_read_reg(inst, idx) || op_write_reg(inst, idx); 
}

RISCVDecoderSimple::decoder_reg RISCVDecoderSimple::get_op_reg(const DecodedInst * inst, unsigned int idx)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  if (idx == 0) return dec->rd;
  if (idx == 1) return dec->rs1;
  if (idx == 2) return dec->rs2;
  return 0;
}

unsigned int RISCVDecoderSimple::size_mem_op(const DecodedInst * inst, unsigned int mem_idx)
{
  riscv::decode *dec = ((RISCVDecodedInstSimple *)inst)->get_decode();
  int op = dec->op;
  // Use generated memory size array
  if (op > 0 && op < sizeof(riscv::rv_inst_mem_size)/sizeof(riscv::rv_inst_mem_size[0])) {
    return riscv::rv_inst_mem_size[op];
  }
  return 4;  // Default
}

unsigned int RISCVDecoderSimple::get_exec_microops(const DecodedInst *ins, int numLoads, int numStores) { return 1; }
uint16_t RISCVDecoderSimple::get_operand_size(const DecodedInst *ins) { return 64; }
bool RISCVDecoderSimple::is_cache_flush_opcode(decoder_opcode opcd) { return false; }
bool RISCVDecoderSimple::is_div_opcode(decoder_opcode opcd) 
{ 
  return (opcd == rv_op_div || opcd == rv_op_divu || opcd == rv_op_rem || opcd == rv_op_remu);
}
bool RISCVDecoderSimple::is_pause_opcode(decoder_opcode opcd) { return false; }
bool RISCVDecoderSimple::is_branch_opcode(decoder_opcode opcd) 
{ 
  // Use generated classification array
  if (opcd > 0 && opcd < sizeof(riscv::rv_inst_is_branch)/sizeof(riscv::rv_inst_is_branch[0])) {
    return riscv::rv_inst_is_branch[opcd];
  }
  return false;
}
bool RISCVDecoderSimple::is_fpvector_addsub_opcode(decoder_opcode opcd, const DecodedInst* ins) 
{ 
  // Check if instruction uses FP or Vector registers
  if (opcd > 0 && opcd < sizeof(riscv::rv_inst_has_fpr)/sizeof(riscv::rv_inst_has_fpr[0])) {
    return riscv::rv_inst_has_fpr[opcd] || riscv::rv_inst_has_vpr[opcd];
  }
  return false;
}

bool RISCVDecoderSimple::is_fpvector_muldiv_opcode(decoder_opcode opcd, const DecodedInst* ins) 
{ 
  // Check if instruction uses FP or Vector registers
  if (opcd > 0 && opcd < sizeof(riscv::rv_inst_has_fpr)/sizeof(riscv::rv_inst_has_fpr[0])) {
    return riscv::rv_inst_has_fpr[opcd] || riscv::rv_inst_has_vpr[opcd];
  }
  return false;
}

bool RISCVDecoderSimple::is_fpvector_ldst_opcode(decoder_opcode opcd, const DecodedInst* ins) 
{ 
  // Check if it's a load/store with FP or Vector registers
  if (opcd > 0 && opcd < sizeof(riscv::rv_inst_has_fpr)/sizeof(riscv::rv_inst_has_fpr[0])) {
    bool is_ldst = riscv::rv_inst_is_load[opcd] || riscv::rv_inst_is_store[opcd];
    bool is_fp_or_vec = riscv::rv_inst_has_fpr[opcd] || riscv::rv_inst_has_vpr[opcd];
    return is_ldst && is_fp_or_vec;
  }
  return false;
}
RISCVDecoderSimple::decoder_reg RISCVDecoderSimple::last_reg() { return dl::last_reg; }
uint32_t RISCVDecoderSimple::map_register(decoder_reg reg) { return static_cast<uint32_t>(reg); }
unsigned int RISCVDecoderSimple::num_read_implicit_registers(const DecodedInst* inst) { return 0; }
RISCVDecoderSimple::decoder_reg RISCVDecoderSimple::get_read_implicit_reg(const DecodedInst* inst, unsigned int idx) { return 0; }
unsigned int RISCVDecoderSimple::num_write_implicit_registers(const DecodedInst* inst) { return 0; }
RISCVDecoderSimple::decoder_reg RISCVDecoderSimple::get_write_implicit_reg(const DecodedInst* inst, unsigned int idx) { return 0; }

// ========================================================================
// RISCVDecodedInstSimple
// ========================================================================

RISCVDecodedInstSimple::RISCVDecodedInstSimple(Decoder* d, const uint8_t * code, size_t size, uint64_t address)
  : DecodedInst()
{
  this->m_dec = d;
  this->m_code = code;
  this->m_size = size;
  this->m_address = address;
  this->m_already_decoded = false;
}

RISCVDecodedInstSimple::~RISCVDecodedInstSimple() {}

unsigned int RISCVDecodedInstSimple::inst_num_id() const { return dec.op; }

std::string RISCVDecodedInstSimple::disassembly_to_str() const
{
  std::ostringstream oss;
  if (dec.op > 0 && dec.op < sizeof(riscv::rv_inst_name_sym)/sizeof(riscv::rv_inst_name_sym[0])) {
    oss << riscv::rv_inst_name_sym[dec.op];
  } else {
    oss << "illegal";
  }
  return oss.str();
}

bool RISCVDecodedInstSimple::is_conditional_branch() const
{
  int op = dec.op;
  // Use generated classification array
  if (op > 0 && op < sizeof(riscv::rv_inst_is_branch)/sizeof(riscv::rv_inst_is_branch[0])) {
    return riscv::rv_inst_is_branch[op];
  }
  return false;
}

bool RISCVDecodedInstSimple::is_nop() const
{
  return (dec.op == rv_op_addi && dec.rd == 0 && dec.rs1 == 0 && dec.imm == 0);
}

bool RISCVDecodedInstSimple::is_atomic() const
{
  int op = dec.op;
  // Use generated classification array
  if (op > 0 && op < sizeof(riscv::rv_inst_is_atomic)/sizeof(riscv::rv_inst_is_atomic[0])) {
    return riscv::rv_inst_is_atomic[op];
  }
  return false;
}

bool RISCVDecodedInstSimple::is_prefetch() const { return false; }

bool RISCVDecodedInstSimple::is_serializing() const 
{ 
  int op = dec.op;
  // Use generated classification array
  if (op > 0 && op < sizeof(riscv::rv_inst_is_fence)/sizeof(riscv::rv_inst_is_fence[0])) {
    return riscv::rv_inst_is_fence[op];
  }
  return false;
}

bool RISCVDecodedInstSimple::is_indirect_branch() const { return (dec.op == rv_op_jalr); }

bool RISCVDecodedInstSimple::is_barrier() const 
{ 
  int op = dec.op;
  // Use generated classification array
  if (op > 0 && op < sizeof(riscv::rv_inst_is_fence)/sizeof(riscv::rv_inst_is_fence[0])) {
    return riscv::rv_inst_is_fence[op];
  }
  return false;
}
bool RISCVDecodedInstSimple::src_dst_merge() const { return false; }
bool RISCVDecodedInstSimple::is_X87() const { return false; }
bool RISCVDecodedInstSimple::has_modifiers() const { return false; }
bool RISCVDecodedInstSimple::is_mem_pair() const { return false; }
bool RISCVDecodedInstSimple::is_writeback() const { return false; }

} // namespace dl
