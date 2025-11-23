#include "../../decoder_lib/riscv_decoder_simple.h"
#include "../../decoder_lib/riscv_decoder_generated.h"
#include "qemu_frontend.h"

namespace frontend
{

class Memory
{
   public:
   virtual ~Memory()
   {
   }

   virtual uint32_t handle(unsigned int threadid, void* regs[],
                           dl::DecodedInst* inst) = 0;
};

struct RegisterBuffer final
{
   RegisterBuffer() : array(g_byte_array_new())
   {
   }

   ~RegisterBuffer()
   {
      g_byte_array_unref(array);
   }

   void read(void* reg)
   {
      g_byte_array_set_size(array, 0);
      pluginReadRegister(reg, array);
   }

   uint64_t le64()
   {
      return GUINT64_FROM_LE(*reinterpret_cast<uint64_t*>(array->data));
   }

   GByteArray * const array;
};

class RiscvVector final
{
   public:
   RiscvVector(void* regs[], RegisterBuffer& buffer, uint64_t id)
      : m_regs(regs)
      , m_buffer(buffer)
      , m_id(id + 64)
   {
   }

   uint64_t read(uint8_t width)
   {
      uint64_t value = 0;

      for (uint8_t e = 0; e < width; e++)
      {
         if (m_index >= m_buffer.array->len)
         {
            m_buffer.read(m_regs[m_id]);
            m_id++;
            m_index = 0;
         }

         value |= (m_buffer.array->data[m_index] << (e * 8));
         m_index++;
      }

      return value;
   }

   private:
   void* const* m_regs;
   RegisterBuffer& m_buffer;
   uint64_t m_id;
   uint64_t m_index = UINT64_MAX;
};

template<typename T>
class RiscvMemory final : public Memory
{
   public:
   RiscvMemory(const GArray* regs)
      : m_vlenb(readVlenb(regs, m_buffers[0]))
      , m_vl(pluginFindRegister(regs, "vl", "org.gnu.gdb.riscv.csr"))
      , m_vstart(pluginFindRegister(regs, "vstart", "org.gnu.gdb.riscv.csr"))
      , m_vtype(pluginFindRegister(regs, "vtype", "org.gnu.gdb.riscv.csr"))
   {
   }

   virtual uint32_t handle(unsigned int threadid, void* regs[],
                           dl::DecodedInst* inst) override
   {
      auto riscv_inst = static_cast<dl::RISCVDecodedInstSimple*>(inst);
      auto& dec = *riscv_inst->get_decode();

      // Note: rv_inst_format is defined in riscv_decoder_generated.h or similar
      // These format checks need to be adapted to the actual decoder structure
      // For now, we'll check opcode types directly

      // Load/store instructions
      if (dec.op == riscv::rv_op_lb || dec.op == riscv::rv_op_lh || dec.op == riscv::rv_op_lw || 
          dec.op == riscv::rv_op_lbu || dec.op == riscv::rv_op_lhu || dec.op == riscv::rv_op_lwu ||
          dec.op == riscv::rv_op_ld || dec.op == riscv::rv_op_sb || dec.op == riscv::rv_op_sh ||
          dec.op == riscv::rv_op_sw || dec.op == riscv::rv_op_sd)
      {
         m_buffers[0].read(regs[dec.rs1]);
         T::handleMemory(threadid, dec.imm + m_buffers[0].le64());
         return 1;
      }

      // Atomic instructions
      if (dec.op == riscv::rv_op_amoswap_w || dec.op == riscv::rv_op_amoswap_d ||
          dec.op == riscv::rv_op_amoadd_w || dec.op == riscv::rv_op_amoadd_d)
      {
         m_buffers[0].read(regs[dec.rs1]);
         T::handleMemory(threadid, m_buffers[0].le64());
         return 1;
      }

      // Vector instructions - placeholder for vector handling
      // Vector instruction handling would go here
      // Note: This requires checking if vector extension is enabled

      return 0;
   }

   private:
   static uint64_t readVlenb(const GArray* regs, RegisterBuffer& buffer)
   {
      auto reg = pluginFindRegister(regs, "vlenb", "org.gnu.gdb.riscv.csr");
      if (!reg)
      {
         return 0;
      }

      buffer.read(reg);
      return buffer.le64();
   }

   RegisterBuffer m_buffers[2];
   const uint64_t m_vlenb;
   void* const m_vl;
   void* const m_vstart;
   void* const m_vtype;
};

}

