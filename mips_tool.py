#!/usr/bin/env python3
"""Small educational MIPS assembler/disassembler support library."""
from __future__ import annotations
import ast, re, struct
from pathlib import Path

REGS = {"zero":0,"at":1,"v0":2,"v1":3,"a0":4,"a1":5,"a2":6,"a3":7,
        **{f"t{i}":8+i for i in range(8)}, **{f"s{i}":16+i for i in range(8)},
        "t8":24,"t9":25,"k0":26,"k1":27,"gp":28,"sp":29,"fp":30,"ra":31}
REGS.update({f"r{i}":i for i in range(32)})
OP = {"addi":8,"andi":12,"ori":13,"slti":10,"lui":15,"lw":35,"sw":43,
      "beq":4,"bne":5,"j":2,"jal":3}
FUN = {"add":32,"sub":34,"and":36,"or":37,"slt":42,"sll":0,"srl":2,"jr":8,"syscall":12}
REG_RE = re.compile(r"^\$([A-Za-z0-9]+)$")
DIRECTIVES = {".text", ".data", ".word", ".byte", ".asciiz", ".ascii", ".space", ".align"}

def reg(s):
    m = REG_RE.match(s.strip().lower())
    if not m or m.group(1) not in REGS: raise ValueError(f"invalid register: {s}")
    return REGS[m.group(1)]
def number(s):
    return int(s.strip(), 0)
def string_bytes(s):
    """Decode an .ascii/.asciiz literal into its UTF-8 byte representation."""
    value = ast.literal_eval(s.strip())
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, bytes):
        return value
    raise ValueError("string directive requires a quoted string")
def clean(line):
    return line.split("#", 1)[0].strip()
def split_args(s):
    return [x.strip() for x in re.split(r",\s*|\s+(?=\$|[-+]?\d|0x|[A-Za-z_])", s.strip()) if x.strip()]
def expr(s, labels, pc=0):
    s=s.strip()
    if s in labels: return labels[s]
    try: return number(s)
    except ValueError: raise ValueError(f"unknown label or number: {s}")

def expand(op, a):
    op=op.lower()
    if op == "nop": return [("sll", ["$zero","$zero","0"])]
    if op == "move": return [("add", [a[0],a[1],"$zero"])]
    if op == "li":
        v=number(a[1])
        if -32768 <= v <= 32767: return [("addi",[a[0],"$zero",str(v)])]
        hi=(v >> 16) & 0xffff; lo=v & 0xffff
        return [("lui",[a[0],str(hi)]),("ori",[a[0],a[0],str(lo)])]
    if op == "la": return [("la",a)]
    if op == "b": return [("beq",["$zero","$zero",a[0]])]
    if op in ("blt","bgt","ble","bge"):
        tmp="$at"; cmp={"blt":"slt","bgt":"slt","ble":"slt","bge":"slt"}[op]
        if op in ("blt","bge"): ins=[(cmp,[tmp,a[0],a[1]])]
        else: ins=[(cmp,[tmp,a[1],a[0]])]
        branch="bne" if op in ("blt","bgt") else "beq"
        return ins+[(branch,[tmp,"$zero" if op in ("blt","bgt") else "$zero",a[2]])]
    return [(op,a)]

def tokenize_source(path):
    mode="text"; items=[]; labels={}; pc_text=0; pc_data=0
    raw=[]
    for lineno,line in enumerate(Path(path).read_text().splitlines(),1):
        line=clean(line)
        if not line: continue
        while ":" in line.split()[0]:
            lab, line = line.split(":",1); labels[lab.strip()]=pc_text if mode=="text" else pc_data
            line=line.strip();
            if not line: break
        if not line: continue
        p=line.split(None,1); op=p[0].lower(); rest=p[1] if len(p)>1 else ""
        if op in (".text",".data"): mode=op[1:]; raw.append((mode,op,rest,lineno)); continue
        args=split_args(rest)
        if mode=="text":
            ex=expand(op,args); raw.append((mode,op,args,lineno)); pc_text += 4*len(ex)
        else:
            raw.append((mode,op,args,lineno))
            if op==".word": pc_data += 4*len(args)
            elif op==".byte": pc_data += len(args)
            elif op in (".ascii",".asciiz"):
                val=string_bytes(rest); pc_data += len(val)+(1 if op==".asciiz" else 0)
            elif op==".space": pc_data += number(args[0])
            elif op==".align": pc_data=(pc_data+(1<<number(args[0]))-1)&~((1<<number(args[0]))-1)
            else: raise ValueError(f"line {lineno}: unsupported directive {op}")
    return raw,labels

def encode(op,a,labels,pc):
    op=op.lower()
    if op in FUN:
        if op=="syscall": return FUN[op]
        if op in ("sll","srl"): return (reg(a[1])<<16)|(reg(a[0])<<11)|(number(a[2])<<6)|FUN[op]
        if op=="jr": return (reg(a[0])<<21)|FUN[op]
        return (reg(a[1])<<21)|(reg(a[2])<<16)|(reg(a[0])<<11)|FUN[op]
    if op=="la": raise ValueError("la must be resolved in second pass")
    if op in ("addi","andi","ori","slti"): return OP[op]<<26 | reg(a[1])<<21 | reg(a[0])<<16 | (expr(a[2],labels,pc)&0xffff)
    if op=="lui": return OP[op]<<26 | reg(a[0])<<16 | (expr(a[1],labels,pc)&0xffff)
    if op in ("lw","sw"):
        m=re.match(r"(.+)\((\$[^)]+)\)$",a[1]);
        if not m: raise ValueError(f"bad memory operand: {a[1]}")
        return OP[op]<<26|reg(m.group(2))<<21|reg(a[0])<<16|(expr(m.group(1),labels,pc)&0xffff)
    if op in ("beq","bne"):
        off=(expr(a[2],labels,pc)-pc-4)//4; return OP[op]<<26|reg(a[0])<<21|reg(a[1])<<16|(off&0xffff)
    if op in ("j","jal"): return OP[op]<<26|((expr(a[0],labels,pc)//4)&0x03ffffff)
    raise ValueError(f"unsupported instruction: {op}")

def assemble(path):
    raw, labels=tokenize_source(path); text=[]; data=bytearray(); pc=0
    for mode,op,a,ln in raw:
        if op in (".text", ".data"):
            continue
        if mode=="text":
            for x,aa in expand(op,a):
                if x=="la":
                    addr=labels.get(aa[1]);
                    if addr is None: raise ValueError(f"line {ln}: unknown label {aa[1]}")
                    text += [encode("lui",[aa[0],str(addr>>16)],labels,pc),encode("ori",[aa[0],aa[0],str(addr&0xffff)],labels,pc+4)]; pc+=8
                else: text.append(encode(x,aa,labels,pc)); pc+=4
        elif op==".word":
            for x in a: data += struct.pack(">I",expr(x,labels))
        elif op==".byte":
            for x in a: data.append(expr(x,labels)&0xff)
        elif op in (".ascii",".asciiz"):
            data += string_bytes(" ".join(a)); data += b"\0" if op==".asciiz" else b""
        elif op==".space": data += b"\0"*number(a[0])
        elif op==".align": data += b"\0"*((-(len(data)))%(1<<number(a[0])))
    return text,bytes(data)

def write_outputs(text,data,ascii_path,bin_path):
    lines=["MIPS-MHC-ASCII v1","TEXT_WORDS %d"%len(text),"DATA_BYTES %d"%len(data),"--TEXT--"]+[f"{x:032b}" for x in text]+["--DATA--",data.hex()]
    Path(ascii_path).write_text("\n".join(lines)+"\n")
    Path(bin_path).write_bytes(b"MHC1"+struct.pack(">II",len(text),len(data))+b"".join(struct.pack(">I",x) for x in text)+data)

def read_image(path):
    b=Path(path).read_bytes()
    if b.startswith(b"MHC1"):
        n,d=struct.unpack(">II",b[4:12]); return list(struct.unpack(">%dI"%n,b[12:12+4*n])),b[12+4*n:12+4*n+d]
    lines=Path(path).read_text().splitlines(); i=lines.index("--TEXT--")+1; j=lines.index("--DATA--"); return [int(x,2) for x in lines[i:j]],bytes.fromhex(lines[j+1] if j+1<len(lines) else "")
