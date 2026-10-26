#!/usr/bin/env python3
import argparse
from mips_tool import assemble, write_outputs

def main():
    p=argparse.ArgumentParser(description="Assemble supported MIPS source into readable and binary MHC files")
    p.add_argument("source"); p.add_argument("--ascii",default="fizzbuzz.mhc-ascii"); p.add_argument("--bin",dest="binary",default="fizzbuzz.mhc-bin")
    a=p.parse_args()
    try:
        text,data=assemble(a.source); write_outputs(text,data,a.ascii,a.binary)
        print(f"assembled {len(text)} instruction words and {len(data)} data bytes")
    except (ValueError, OSError, SyntaxError) as e: p.error(str(e))
if __name__=="__main__": main()
