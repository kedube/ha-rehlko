"""Minimal, read-only parser for a Dart 3.5.4 AOT snapshot (arm64, no compressed pointers).

Parses only the clustered-snapshot *alloc* section so object reference ids can be
mapped to RO-data image objects (strings), then locates the global ObjectPool fill.
Reference: dart-lang/sdk@3.5.4 runtime/vm/app_snapshot.cc, datastream.h, class_id.h.
"""

from __future__ import annotations

import os
import struct
import sys

# The Dart AOT binary inside the installed app bundle. Override the bundle path with
# REHLKO_APP if it is installed elsewhere. The section offsets below (from `otool -l` on the
# App binary) are specific to app version 1.6.202610; see docs/reverse-engineering.md.
_APP_BUNDLE = os.environ.get("REHLKO_APP", "/Applications/Energy Mgmt..app")
APP = f"{_APP_BUNDLE}/Wrapper/Runner.app/Frameworks/App.framework/App"
ISO_DATA = 0x6766C0
ISO_DATA_END = 0x9E3E40
ISO_INSTR = 0xE900
ISO_INSTR_END = 0x66D950

# --- class ids for Dart 3.5.4 -------------------------------------------------------
_names = ["Illegal", "NativePointer", "FreeListElement", "ForwardingCorpse", "Object"]
_names += """Class PatchClass Function TypeParameters ClosureData FfiTrampolineData Field Script
Library Namespace KernelProgramInfo WeakSerializationReference WeakArray Code Instructions
InstructionsSection InstructionsTable ObjectPool PcDescriptors CodeSourceMap CompressedStackMaps
LocalVarDescriptors ExceptionHandlers Context ContextScope Sentinel SingleTargetCache UnlinkedCall
MonomorphicSmiableCall CallSiteData ICData MegamorphicCache SubtypeTestCache LoadingUnit Error
ApiError LanguageError UnhandledException UnwindError""".split()
_names += """Instance LibraryPrefix TypeArguments AbstractType Type FunctionType RecordType
TypeParameter FinalizerBase Finalizer NativeFinalizer FinalizerEntry Closure Number Integer Smi
Mint Double Bool Float32x4 Int32x4 Float64x2 Record TypedDataBase TypedData ExternalTypedData
TypedDataView Pointer DynamicLibrary Capability ReceivePort SendPort StackTrace SuspendState RegExp
WeakProperty WeakReference MirrorReference FutureOr UserTag TransferableTypedData""".split()
_names += "Map ConstMap Set ConstSet Array ImmutableArray GrowableObjectArray String OneByteString TwoByteString".split()
_names += ["FfiNativeFunction"] + [f"Ffi{n}" for n in "Int8 Int16 Int32 Int64 Uint8 Uint16 Uint32 Uint64 Float Double Void Handle Bool".split()]
_names += ["FfiNativeType", "FfiStruct"]
for t in "Int8 Uint8 Uint8Clamped Int16 Uint16 Int32 Uint32 Int64 Uint64 Float32 Float64 Float32x4 Int32x4 Float64x2".split():
    _names += [f"TypedData{t}Array", f"TypedData{t}ArrayView", f"ExternalTypedData{t}Array", f"UnmodifiableTypedData{t}ArrayView"]
_names += ["ByteDataView", "UnmodifiableByteDataView", "ByteBuffer", "Null", "Dynamic", "Void", "Never"]
CID = {n: i for i, n in enumerate(_names)}
NUM_PREDEFINED = len(_names)
assert CID["ObjectPool"] == 22 and CID["OneByteString"] == 93 and NUM_PREDEFINED == 174, (CID["ObjectPool"], CID["OneByteString"], NUM_PREDEFINED)
FIRST_TD = CID["TypedDataInt8Array"]
LAST_TD = CID["UnmodifiableTypedDataFloat64x2ArrayView"]


def cid_name(c: int) -> str:
    return _names[c] if c < NUM_PREDEFINED else f"UserClass#{c}"


class Stream:
    def __init__(self, buf: bytes, pos: int = 0) -> None:
        self.b = buf
        self.p = pos

    def byte(self) -> int:
        v = self.b[self.p]
        self.p += 1
        return v

    def _read(self, end_marker: int, bits: int, signed: bool) -> int:
        b = self.byte()
        if b > 127:
            v = b - end_marker
        else:
            r, s = 0, 0
            while b <= 127:
                r |= b << s
                s += 7
                b = self.byte()
            v = r | ((b - end_marker) << s)
        mask = (1 << bits) - 1
        v &= mask
        if signed and v >> (bits - 1):
            v -= 1 << bits
        return v

    def unsigned(self) -> int:
        return self._read(128, 64, False)

    def read32(self, signed: bool = True) -> int:
        return self._read(192, 32, signed)

    def read64(self, signed: bool = True) -> int:
        return self._read(192, 64, signed)

    def ref(self) -> int:
        result = 0
        for _ in range(4):
            byte = self.byte()
            if byte >= 128:
                byte -= 256
            result = byte + (result << 7)
            if byte < 0:
                return result + 128
        raise ValueError("bad ref")


def load() -> bytes:
    with open(APP, "rb") as fh:
        return fh.read()


VM_DATA = 0x66D980
VM_DATA_END = 0x6766C0


def parse_alloc(buf: bytes, verbose: bool = False, region=(ISO_DATA, ISO_DATA_END)):
    data = buf[region[0]:region[1]]
    magic, length, kind = struct.unpack_from("<iqq", data, 0)
    assert magic == -0x23230A0B, hex(magic & 0xFFFFFFFF)
    total_len = length + 4
    hdr = 20
    version = data[hdr:hdr + 32].decode()
    feat_end = data.index(b"\0", hdr + 32)
    features = data[hdr + 32:feat_end].decode()
    st = Stream(data, feat_end + 1)
    num_base = st.unsigned()
    num_objects = st.unsigned()
    num_clusters = st.unsigned()
    instr_table_len = st.unsigned()
    instr_table_data_off = st.unsigned()
    if verbose:
        print(f"version={version} features='{features}' kind={kind} len={total_len}")
        print(f"base={num_base} objects={num_objects} clusters={num_clusters} itab={instr_table_len} itab_off={instr_table_data_off}")
    next_ref = 1 + num_base
    objs = {}  # ref id -> (cid, extra)
    clusters = []
    for ci in range(num_clusters):
        start_pos = st.p
        tags = st.read32(signed=False)
        cid = (tags >> 12) & 0xFFFFF
        canonical = bool(tags & 2)
        start_ref = next_ref
        info = {}

        def assign(n, extra=None):
            nonlocal next_ref
            for _ in range(n):
                objs[next_ref] = (cid, extra)
                next_ref += 1

        def canonical_set():
            # BuildCanonicalSetFromLayout: only for canonical clusters in the root unit.
            if canonical:
                table_length = st.unsigned()
                first_element = st.unsigned()
                count = next_ref - (start_ref + first_element)
                for _ in range(count):
                    st.unsigned()
                info["table_length"] = table_length

        if cid >= NUM_PREDEFINED or cid == CID["Instance"] or (CID["FfiInt8"] <= cid <= CID["FfiBool"]):
            count = st.unsigned()
            info["next_field_words"] = st.read32()
            info["size_words"] = st.read32()
            assign(count)
        elif cid == CID["ByteDataView"] or (FIRST_TD <= cid <= LAST_TD and (cid - FIRST_TD) % 4 == 1):
            assign(st.unsigned())
        elif FIRST_TD <= cid <= LAST_TD and (cid - FIRST_TD) % 4 == 2:
            assign(st.unsigned())
        elif FIRST_TD <= cid <= LAST_TD and (cid - FIRST_TD) % 4 == 0:
            count = st.unsigned()
            for _ in range(count):
                st.unsigned()
                assign(1)
        elif cid in (CID["PcDescriptors"], CID["CodeSourceMap"], CID["CompressedStackMaps"],
                     CID["OneByteString"], CID["TwoByteString"], CID["String"]):
            # RODataDeserializationCluster (root unit, includes code, no compressed ptrs)
            count = st.unsigned()
            running = 0
            for _ in range(count):
                running += st.unsigned() << 4
                objs[next_ref] = (cid, running)
                next_ref += 1
            if cid == CID["String"]:
                canonical_set()
        elif cid == CID["Class"]:
            count = st.unsigned()
            for _ in range(count):
                st.read32()
                assign(1)
            assign(st.unsigned())
        elif cid in (CID["TypeArguments"],):
            count = st.unsigned()
            for _ in range(count):
                st.unsigned()
                assign(1)
            canonical_set()
        elif cid == CID["Code"]:
            count = st.unsigned()
            for _ in range(count):
                st.read32()
                assign(1)
            info["code_count"] = count
            dcount = st.unsigned()
            for _ in range(dcount):
                st.read32()
                assign(1)
        elif cid in (CID["ObjectPool"], CID["ExceptionHandlers"], CID["Context"], CID["ContextScope"],
                     CID["Record"], CID["Array"], CID["ImmutableArray"], CID["WeakArray"]):
            count = st.unsigned()
            lengths = []
            for _ in range(count):
                n = st.unsigned()
                lengths.append(n)
                assign(1, n)
            info["lengths"] = lengths[:5]
            if cid in (CID["Record"], CID["Array"], CID["ImmutableArray"]) and False:
                pass
        elif cid == CID["Mint"]:
            count = st.unsigned()
            for _ in range(count):
                v = st.read64()
                objs[next_ref] = (cid, v)
                next_ref += 1
        elif cid == 1:  # DeltaEncodedTypedData
            count = st.unsigned()
            for _ in range(count):
                st.unsigned()
                assign(1)
        elif cid in (CID["Type"], CID["FunctionType"], CID["RecordType"], CID["TypeParameter"]):
            assign(st.unsigned())
            canonical_set()
        elif cid in (CID["TypeParameters"], CID["PatchClass"], CID["Function"], CID["ClosureData"],
                     CID["FfiTrampolineData"], CID["Field"], CID["Script"], CID["Library"],
                     CID["Namespace"], CID["KernelProgramInfo"], CID["UnlinkedCall"], CID["ICData"],
                     CID["MegamorphicCache"], CID["SubtypeTestCache"], CID["LoadingUnit"],
                     CID["LanguageError"], CID["UnhandledException"], CID["LibraryPrefix"],
                     CID["Closure"], CID["Double"], CID["Int32x4"], CID["Float32x4"], CID["Float64x2"],
                     CID["GrowableObjectArray"], CID["StackTrace"], CID["RegExp"], CID["WeakProperty"],
                     CID["ConstMap"], CID["ConstSet"]):
            assign(st.unsigned())
        else:
            raise ValueError(f"cluster {ci}: unhandled cid {cid} ({cid_name(cid)}) at {start_pos:#x}")
        # Records, Arrays, Closures, Doubles, Mints, Instances etc. may also be canonical
        # sets (BuildCanonicalSetFromLayout) only for String/Type*/TypeArguments in 3.5.4.
        clusters.append((ci, cid, canonical, start_ref, next_ref, info, start_pos))
        if verbose:
            print(f"#{ci:3d} {cid_name(cid):28s} canon={int(canonical)} refs {start_ref}..{next_ref - 1} ({next_ref - start_ref}) {info if info else ''}")
    assert next_ref - 1 == num_objects, (next_ref - 1, num_objects)
    data_image = (total_len + 63) // 64 * 64
    return {
        "data": data,
        "objs": objs,
        "clusters": clusters,
        "fill_start": st.p,
        "num_base": num_base,
        "num_objects": num_objects,
        "data_image": data_image,
    }


if __name__ == "__main__":
    r = parse_alloc(load(), verbose=True)
    print("fill section starts at", hex(r["fill_start"]), "data image at", hex(r["data_image"]))
