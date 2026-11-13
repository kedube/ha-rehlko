"""Recover enum constant tables ({index, _name, value}) from Instance cluster fills.

Scans the fill section for runs of [index (unboxed: two Read32 varints)][ref _name][ref value]
where both refs resolve to strings (value may be null), grouped into consecutive runs.
"""

from __future__ import annotations

import re
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import dartsnap as D  # noqa: E402

buf = D.load()
r = D.parse_alloc(buf)
vm = D.parse_alloc(buf, region=(D.VM_DATA, D.VM_DATA_END))
data, objs, img = r["data"], r["objs"], r["data_image"]
total_len = struct.unpack_from("<q", data, 4)[0] + 4
NUM_BASE = r["num_base"]


def s_at(dat, image, off):
    tags, = struct.unpack_from("<Q", dat, image + off)
    c = (tags >> 12) & 0xFFFFF
    n = struct.unpack_from("<q", dat, image + off + 8)[0] >> 1
    if c == D.CID["OneByteString"]:
        return dat[image + off + 16:image + off + 16 + n].decode("latin-1")
    if c == D.CID["TwoByteString"]:
        return dat[image + off + 16:image + off + 16 + 2 * n].decode("utf-16-le", "replace")
    return None


def string_of(ref):
    if ref == 1:
        return None  # null
    if ref <= NUM_BASE:
        cid, off = vm["objs"].get(ref, (None, None))
        if cid in (92, 93, 94) and off is not None:
            return s_at(vm["data"], vm["data_image"], off)
        return False
    cid, off = objs.get(ref, (None, None))
    if cid in (92, 93, 94) and off is not None:
        return s_at(data, img, off)
    return False


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def try_instance(pos):
    """Return (index, name, value, next_pos) if an enum instance starts at pos."""
    st = D.Stream(data, pos)
    try:
        if BOXED:
            iref = st.ref()
            cid, v = objs.get(iref, (None, None))
            if cid != D.CID["Mint"] or not (0 <= v <= 400):
                return None
            lo = v
        else:
            lo = st.read32(signed=False)
            hi = st.read32(signed=False)
            if hi != 0 or lo > 400:
                return None
        name = string_of(st.ref())
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", name):
            return None
        vref = st.ref()
        value = string_of(vref)
        if value is False:
            return None
        return lo, name, value, st.p
    except (IndexError, ValueError):
        return None


BOXED = len(sys.argv) > 2 and sys.argv[2] == "boxed"
runs = []
pos = r["fill_start"]
end = total_len
while pos < end - 4:
    first = try_instance(pos)
    if not first:
        pos += 1
        continue
    run = [first[:3]]
    p = first[3]
    while True:
        nxt = try_instance(p)
        if not nxt:
            break
        run.append(nxt[:3])
        p = nxt[3]
    idx = sorted(i for i, _, _ in run)
    if len(run) >= 2 and idx == list(range(len(run))):
        runs.append((pos, sorted(run)))
        pos = p
    else:
        pos += 1

with open(sys.argv[1], "w", encoding="utf-8") as fh:
    for pos, run in runs:
        vals = ", ".join(f"{n}={v!r}" if v is not None and norm(v) != norm(n) else (f"{n}=null" if v is None else f"{n}={v!r}") for _, n, v in run)
        fh.write(f"@{pos:#x} [{len(run)}] {vals}\n")
print("enum runs:", len(runs))
