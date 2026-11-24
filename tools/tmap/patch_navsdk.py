#!/usr/bin/env python3
"""Apply the time-weighted fix-rate patch to TMAP's libNavigationSDK.so (arm64).

Input : lib/arm64-v8a/libNavigationSDK.so from split_config.arm64_v8a.apk of
        com.skt.tmap.ku 11.8.4.4075 (sha256 checked).
Output: patched .so. The patch list is data in navsdk_11.8.4.4075.json (offset / orig / new hex),
        so a Kotlin (Morphe) patch can apply exactly the same list.
Design and every site: docs/tmap/N2_patch.md.

usage: patch_navsdk.py IN.so [OUT.so] [--json PATCHES.json] [--force-hash]
"""
import argparse
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_JSON = os.path.join(HERE, "navsdk_11.8.4.4075.json")


def check_elf(data, slot_va, slot_size):
    """Sanity checks on the header-level edit: the slot lies inside the last RW PT_LOAD and the
    segment end does not move to another page (load size and alignment unchanged)."""
    assert data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1, "not ELF64 LE"
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 0x36)
    loads = []
    for i in range(phnum):
        p_type, p_flags, p_off, p_va, _pa, p_fs, p_ms, p_al = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phentsize)
        if p_type == 1:
            loads.append((p_flags, p_off, p_va, p_fs, p_ms, p_al))
    flags, off, va, fs, ms, al = loads[-1]
    assert flags & 2, "last PT_LOAD not writable"
    assert va <= slot_va and slot_va + slot_size <= va + ms, "slot outside last PT_LOAD"
    assert (va + ms + 0xFFF) // 0x1000 == (va + ms - slot_size + 0xFFF) // 0x1000, "memsz grew across a page"
    assert off % al == va % al
    return loads


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--json", default=DEFAULT_JSON)
    ap.add_argument("--force-hash", action="store_true", help="continue on input sha256 mismatch (orig bytes are still checked)")
    a = ap.parse_args()

    spec = json.load(open(a.json, encoding="utf-8"))
    data = bytearray(open(a.input, "rb").read())
    h = hashlib.sha256(data).hexdigest()
    print("input  %s  sha256 %s" % (a.input, h))
    if h == spec["sha256_out"]:
        print("already patched; nothing to do")
        return 0
    if h != spec["sha256_in"]:
        print("sha256 mismatch: expected %s" % spec["sha256_in"])
        if not a.force_hash:
            return 2
    if len(data) != spec["size"]:
        print("size mismatch: %d != %d" % (len(data), spec["size"]))
        return 2

    # verify every original byte range before writing anything
    bad = []
    for p in spec["patches"]:
        o, old = p["offset"], bytes.fromhex(p["orig"])
        if bytes(data[o:o + len(old)]) != old:
            bad.append(p)
    if bad:
        for p in bad:
            print("orig mismatch at 0x%x (%s): %s" % (p["offset"], p["id"], p["desc"]))
        return 3

    count = {}
    for p in spec["patches"]:
        o, new = p["offset"], bytes.fromhex(p["new"])
        assert len(new) == len(bytes.fromhex(p["orig"]))
        data[o:o + len(new)] = new
        count[p["id"]] = count.get(p["id"], 0) + 1
        print("  0x%06x %-5s %4d B  %s" % (o, p["id"], len(new), p["desc"]))

    check_elf(data, int(spec["slot"]["va"], 16), spec["slot"]["size"])
    out_hash = hashlib.sha256(data).hexdigest()
    if out_hash != spec["sha256_out"]:
        print("output sha256 %s != expected %s" % (out_hash, spec["sha256_out"]))
        if not a.force_hash:
            return 4

    out = a.output or os.path.splitext(a.input)[0] + ".patched.so"
    with open(out, "wb") as f:
        f.write(data)
    print("output %s  sha256 %s" % (out, out_hash))
    print("summary: %d patch entries; " % len(spec["patches"]) + ", ".join("%s x%d" % kv for kv in sorted(count.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
