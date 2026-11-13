"""Scan arm64 Dart AOT code for object-pool (x27) loads and group pool strings by function.

Output: one block per function (split at the standard Dart frame prologue), listing the
pool strings (and a few other pool object kinds) in the order the code loads them.
"""

from __future__ import annotations

import pickle
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import dartsnap as D  # noqa: E402

PP = 27
pool = pickle.load(open(sys.argv[1], "rb"))
entries, strings = pool["entries"], pool["strings"]
out_path = sys.argv[2]

buf = D.load()
code = buf[D.ISO_INSTR:D.ISO_INSTR_END]
n = len(code) // 4
words = struct.unpack_from(f"<{n}I", code, 0)

PROLOGUE = 0xA9BF79FD  # stp x29, x30, [x15, #-0x10]!  (Dart arm64 SP is x15)


def idx_for(offset: int):
    if offset < 16 or (offset - 16) % 8:
        return None
    return (offset - 16) // 8


funcs = []
cur = {"start": 0, "items": []}
pending_add = {}  # reg -> base offset (add xD, x27, #imm, lsl 12)
for i, w in enumerate(words):
    if w == PROLOGUE:
        if cur["items"]:
            funcs.append(cur)
        cur = {"start": i * 4, "items": []}
        pending_add.clear()
    # add Xd, X27, #imm12, lsl #12
    if (w & 0xFFC003E0) == 0x91400000 | (PP << 5):
        rd = w & 0x1F
        pending_add[rd] = ((w >> 10) & 0xFFF) << 12
        continue
    # ldr Xt, [Xn, #imm12*8]
    if (w & 0xFFC00000) == 0xF9400000:
        rn = (w >> 5) & 0x1F
        off = ((w >> 10) & 0xFFF) * 8
        base = 0 if rn == PP else pending_add.get(rn)
        if base is not None:
            ix = idx_for(base + off)
            if ix is not None and ix < len(entries):
                s = strings.get(ix)
                if s is not None:
                    cur["items"].append((i * 4, s))
        if rn in pending_add and rn != PP:
            pending_add.pop(rn, None)
        continue
if cur["items"]:
    funcs.append(cur)

with open(out_path, "w", encoding="utf-8") as fh:
    for f in funcs:
        seq = [s for _, s in f["items"]]
        fh.write(f"@{D.ISO_INSTR + f['start']:#x} | " + " ¦ ".join(repr(s)[1:-1] for s in seq) + "\n")
print("functions with string refs:", len(funcs))
