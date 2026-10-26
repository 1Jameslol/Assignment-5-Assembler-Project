#!/usr/bin/env python3
import argparse
from pathlib import Path
from mips_tool import read_image

R={0:"zero",1:"at",2:"v0",3:"v1",4:"a0",5:"a1",6:"a2",7:"a3",**{8+i:f"t{i}" for i in range(8)},**{16+i:f"s{i}" for i in range(8)},24:"t8",25:"t9",29:"sp",31:"ra"}
OPS={8:"addi",12:"andi",13:"ori",10:"slti",15:"lui",35:"lw",43:"sw",4:"beq",5:"bne",2:"j",3:"jal"}
FUN={32:"add",34:"sub",36:"and",37:"or",42:"slt",0:"sll",2:"srl",8:"jr",12:"syscall"}
def r(n): return "$"+R.get(n,f"r{n}")
def decode(w,pc):
    op=w>>26; rs=(w>>21)&31; rt=(w>>16)&31; rd=(w>>11)&31; fn=w&63; imm=w&65535
    simm=imm-65536 if imm&32768 else imm
    if op==0:
        if fn==12:return "syscall"
        if fn==8:return f"jr {r(rs)}"
        if fn in (0,2):return f"{FUN[fn]} {r(rd)}, {r(rt)}, {(w>>6)&31}"
        return f"{FUN.get(fn,'unknown')} {r(rd)}, {r(rs)}, {r(rt)}"
    if op in (8,12,13,10):return f"{OPS[op]} {r(rt)}, {r(rs)}, {simm if op in (8,10) else imm}"
    if op==15:return f"lui {r(rt)}, {imm}"
    if op in (35,43):return f"{OPS[op]} {r(rt)}, {simm}({r(rs)})"
    if op in (4,5):return f"{OPS[op]} {r(rs)}, {r(rt)}, {pc+4+simm*4:#x}"
    if op in (2,3):return f"{OPS[op]} {(w&0x03ffffff)*4:#x}"
    return f".word 0x{w:08x}"
def main():
    p=argparse.ArgumentParser(description="Disassemble MHC ASCII or binary output"); p.add_argument("image"); p.add_argument("-o",default="reconstructed.s"); a=p.parse_args()
    try:
        text,data=read_image(a.image); out=[".text"]
        for i,w in enumerate(text): out.append(f"    {decode(w,i*4)}")
        out += ["", ".data", "    # Data bytes are preserved exactly by the MHC container.", "    .byte " + ", ".join(f"0x{x:02x}" for x in data) if data else "    # no data"]
        Path(a.o).write_text("\n".join(out)+"\n"); print(f"disassembled {len(text)} instruction words and {len(data)} data bytes")
    except (ValueError, OSError) as e: p.error(str(e))
if __name__=="__main__": main()
