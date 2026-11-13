"""Locate and decode the global ObjectPool, then map pool indices to strings."""

from __future__ import annotations

import json
import pickle
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import dartsnap as D  # noqa: E402

buf = D.load()
r = D.parse_alloc(buf)
data, objs, img = r["data"], r["objs"], r["data_image"]
num_objects = r["num_objects"]
POOL_LEN = 39323
total_len = struct.unpack_from("<q", data, 4)[0] + 4


def enc_unsigned(v: int) -> bytes:
    out = bytearray()
    while v > 127:
        out.append(v & 0x7F)
        v >>= 7
    out.append(v + 128)
    return bytes(out)


def ro_string(off: int):
    tags, = struct.unpack_from("<Q", data, img + off)
    cid = (tags >> 12) & 0xFFFFF
    smi, = struct.unpack_from("<q", data, img + off + 8)
    n = smi >> 1
    if cid == D.CID["OneByteString"]:
        return data[img + off + 16: img + off + 16 + n].decode("latin-1")
    if cid == D.CID["TwoByteString"]:
        return data[img + off + 16: img + off + 16 + 2 * n].decode("utf-16-le", "replace")
    return None


vm = D.parse_alloc(buf, region=(D.VM_DATA, D.VM_DATA_END))
vm_data, vm_objs, vm_img = vm["data"], vm["objs"], vm["data_image"]
print("vm snapshot: base", vm["num_base"], "objects", vm["num_objects"], "image", hex(vm_img))


def vm_string(ref: int):
    cid, off = vm_objs.get(ref, (None, None))
    if cid not in (D.CID["String"], D.CID["OneByteString"], D.CID["TwoByteString"]) or off is None:
        return None
    tags, = struct.unpack_from("<Q", vm_data, vm_img + off)
    c = (tags >> 12) & 0xFFFFF
    smi, = struct.unpack_from("<q", vm_data, vm_img + off + 8)
    n = smi >> 1
    if c == D.CID["OneByteString"]:
        return vm_data[vm_img + off + 16: vm_img + off + 16 + n].decode("latin-1")
    if c == D.CID["TwoByteString"]:
        return vm_data[vm_img + off + 16: vm_img + off + 16 + 2 * n].decode("utf-16-le", "replace")
    return None


def try_decode(pos: int):
    st = D.Stream(data, pos)
    if st.unsigned() != POOL_LEN:
        return None
    entries = []
    for _ in range(POOL_LEN):
        bits = st.byte()
        typ, behavior = bits & 0xF, (bits >> 5) & 7
        if behavior not in (0, 2, 3, 4) or typ > 2:
            return None
        if behavior != 0:
            entries.append(("special", behavior))
            continue
        if typ == 1:
            ref = st.ref()
            if not (1 <= ref <= num_objects):
                return None
            entries.append(("obj", ref))
        elif typ == 0:
            entries.append(("imm", st.read64()))
        else:
            entries.append(("native", None))
    return entries, st.p


needle = enc_unsigned(POOL_LEN)
start = r["fill_start"]
hits = []
p = data.find(needle, start, total_len)
while p != -1:
    res = try_decode(p)
    if res:
        hits.append((p, res))
        print(f"valid pool decode at {p:#x}, ends {res[1]:#x}")
    p = data.find(needle, p + 1, total_len)
print("candidates:", len(hits))
if hits:
    pos, (entries, end) = hits[-1]
    pool_strings = {}
    kinds = {}
    for i, (kind, val) in enumerate(entries):
        if kind == "obj":
            if val <= r["num_base"]:
                vs = vm_string(val)
                if vs is not None:
                    pool_strings[i] = vs
                kinds["vm-base"] = kinds.get("vm-base", 0) + 1
                continue
            cid, extra = objs.get(val, (None, None))
            kinds[D.cid_name(cid) if cid is not None else "base"] = kinds.get(D.cid_name(cid) if cid is not None else "base", 0) + 1
            if cid in (D.CID["String"], D.CID["OneByteString"], D.CID["TwoByteString"]) and extra is not None:
                s = ro_string(extra)
                if s is not None:
                    pool_strings[i] = s
    print("pool object kinds:", sorted(kinds.items(), key=lambda kv: -kv[1])[:15])
    print("strings in pool:", len(pool_strings))
    with open(sys.argv[1], "wb") as fh:
        pickle.dump({"entries": entries, "strings": pool_strings}, fh)
    for i in list(pool_strings)[:10]:
        print(i, repr(pool_strings[i]))
