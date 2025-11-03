#ifndef _RISCV_DECODER_SIMPLE_H_
#define _RISCV_DECODER_SIMPLE_H_

#include "decoder.h"
#include "riscv_decoder_generated.h"
#include <cstddef>

namespace dl
{

enum reg_num
{
  rv_ireg_x0,  rv_ireg_x1,  rv_ireg_x2,  rv_ireg_x3,  
  rv_ireg_x4,  rv_ireg_x5,  rv_ireg_x6,  rv_ireg_x7,
  rv_ireg_x8,  rv_ireg_x9,  rv_ireg_x10, rv_ireg_x11, 
  rv_ireg_x12, rv_ireg_x13, rv_ireg_x14, rv_ireg_x15,
  rv_ireg_x16, rv_ireg_x17, rv_ireg_x18, rv_ireg_x19, 
  rv_ireg_x20, rv_ireg_x21, rv_ireg_x22, rv_ireg_x23,
  rv_ireg_x24, rv_ireg_x25, rv_ireg_x26, rv_ireg_x27, 
  rv_ireg_x28, rv_ireg_x29, rv_ireg_x30, rv_ireg_x31,
  rv_freg_f0,  rv_freg_f1,  rv_freg_f2,  rv_freg_f3,  
  rv_freg_f4,  rv_freg_f5,  rv_freg_f6,  rv_freg_f7,
  rv_freg_f8,  rv_freg_f9,  rv_freg_f10, rv_freg_f11, 
  rv_freg_f12, rv_freg_f13, rv_freg_f14, rv_freg_f15,
  rv_freg_f16, rv_freg_f17, rv_freg_f18, rv_freg_f19, 
  rv_freg_f20, rv_freg_f21, rv_freg_f22, rv_freg_f23,
  rv_freg_f24, rv_freg_f25, rv_freg_f26, rv_freg_f27, 
  rv_freg_f28, rv_freg_f29, rv_freg_f30, rv_freg_f31,
  rv_vreg_v0,  rv_vreg_v1,  rv_vreg_v2,  rv_vreg_v3,  
  rv_vreg_v4,  rv_vreg_v5,  rv_vreg_v6,  rv_vreg_v7,
  rv_vreg_v8,  rv_vreg_v9,  rv_vreg_v10, rv_vreg_v11, 
  rv_vreg_v12, rv_vreg_v13, rv_vreg_v14, rv_vreg_v15,
  rv_vreg_v16, rv_vreg_v17, rv_vreg_v18, rv_vreg_v19, 
  rv_vreg_v20, rv_vreg_v21, rv_vreg_v22, rv_vreg_v23,
  rv_vreg_v24, rv_vreg_v25, rv_vreg_v26, rv_vreg_v27, 
  rv_vreg_v28, rv_vreg_v29, rv_vreg_v30, rv_vreg_v31,
  last_reg
};

extern const char* reg_name_sym[];  

class RISCVDecoderSimple : public Decoder
{
  public:    
    RISCVDecoderSimple(dl_arch arch, dl_mode mode, dl_syntax syntax);
    unsigned int reg_set_size = 96;  // 32 int + 32 float + 32 vector   
    virtual ~RISCVDecoderSimple();
    
    virtual void decode(DecodedInst * inst) override;
    virtual void decode(DecodedInst * inst, dl_isa isa) override;
    virtual void change_isa_mode(dl_isa new_isa) override; 
    virtual const char* inst_name(unsigned int inst_id) override; 
    virtual const char* reg_name(unsigned int reg_id) override;
    
    // Decoder基底クラスの仮想関数
    virtual decoder_reg largest_enclosing_register(decoder_reg r) override;
    virtual bool invalid_register(decoder_reg r) override;
    virtual bool reg_is_program_counter(decoder_reg r) override;
    virtual bool inst_in_group (const DecodedInst * inst, unsigned int group_id) override;
    virtual unsigned int num_operands (const DecodedInst * inst) override;
    virtual unsigned int num_memory_operands (const DecodedInst * inst) override;
    virtual decoder_reg mem_base_reg (const DecodedInst * inst, unsigned int mem_idx) override;
    virtual bool mem_base_upate(const DecodedInst* inst, unsigned int mem_idx) override;
    virtual bool has_index_reg (const DecodedInst * inst, unsigned int mem_idx) override;
    virtual decoder_reg mem_index_reg (const DecodedInst * inst, unsigned int mem_idx) override;
    virtual bool op_read_mem (const DecodedInst * inst, unsigned int mem_idx) override;
    virtual bool op_write_mem (const DecodedInst * inst, unsigned int mem_idx) override;
    virtual bool op_read_reg (const DecodedInst * inst, unsigned int idx) override;
    virtual bool op_write_reg (const DecodedInst * inst, unsigned int idx) override;
    virtual bool is_addr_gen (const DecodedInst * inst, unsigned int idx) override;
    virtual bool op_is_reg (const DecodedInst * inst, unsigned int idx) override;    
    virtual decoder_reg get_op_reg (const DecodedInst * inst, unsigned int idx) override;
    virtual unsigned int size_mem_op (const DecodedInst * inst, unsigned int mem_idx) override;
    virtual unsigned int get_exec_microops(const DecodedInst *ins, int numLoads, int numStores) override;
    virtual uint16_t get_operand_size(const DecodedInst *ins) override;
    virtual bool is_cache_flush_opcode(decoder_opcode opcd) override;
    virtual bool is_div_opcode(decoder_opcode opcd) override;
    virtual bool is_pause_opcode(decoder_opcode opcd) override;
    virtual bool is_branch_opcode(decoder_opcode opcd) override;
    virtual bool is_fpvector_addsub_opcode(decoder_opcode opcd, const DecodedInst* ins) override;
    virtual bool is_fpvector_muldiv_opcode(decoder_opcode opcd, const DecodedInst* ins) override;    
    virtual bool is_fpvector_ldst_opcode(decoder_opcode opcd, const DecodedInst* ins) override;
    virtual decoder_reg last_reg() override;
    virtual uint32_t map_register(decoder_reg reg) override;
    virtual unsigned int num_read_implicit_registers(const DecodedInst* inst) override;
    virtual decoder_reg get_read_implicit_reg(const DecodedInst* inst, unsigned int idx) override;
    virtual unsigned int num_write_implicit_registers(const DecodedInst* inst) override;
    virtual decoder_reg get_write_implicit_reg(const DecodedInst* inst, unsigned int idx) override;
};

class RISCVDecodedInstSimple : public DecodedInst
{
  private:
    riscv::decode dec;

  public:
    RISCVDecodedInstSimple(Decoder* d, const uint8_t * code, size_t size, uint64_t address);
    virtual ~RISCVDecodedInstSimple();
    
    void set_decode(riscv::decode d) { dec = d; }
    riscv::decode* get_decode() { return &dec; }
    
    // DecodedInst基底クラスの仮想関数
    virtual unsigned int inst_num_id() const override;
    virtual std::string disassembly_to_str() const override;
    virtual bool is_nop() const override;
    virtual bool is_atomic() const override;
    virtual bool is_prefetch() const override;
    virtual bool is_serializing() const override;
    virtual bool is_conditional_branch() const override;
    virtual bool is_indirect_branch() const override;
    virtual bool is_barrier() const override;
    virtual bool src_dst_merge() const override;
    virtual bool is_X87() const override;
    virtual bool has_modifiers() const override;
    virtual bool is_mem_pair() const override;
    virtual bool is_writeback() const override;
};

} // namespace dl

#endif // _RISCV_DECODER_SIMPLE_H_
