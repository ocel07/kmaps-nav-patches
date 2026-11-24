import json, hashlib, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
# original lib/arm64-v8a/libNavigationSDK.so of TMAP 11.8.4.4075: first argument or env TMAP_NAVSDK_SO
SO = sys.argv[1] if len(sys.argv) > 1 else os.environ["TMAP_NAVSDK_SO"]
OUT = os.path.join(HERE, "..", "navsdk_11.8.4.4075.json")
orig = open(SO, "rb").read()
blocks = json.load(open(os.path.join(HERE, "blocks.json")))["blocks"]

DESC = {
    "f7c74": ("W", "CNaviModule::MapMatch: BL CRuntimeEnv::GetInstance -> BL cave_w (w = clamp(fix_ms - prev_ms, 1..1000))"),
    "f7f10": ("N2-10", "CNaviModule::MapMatch: route-track counter -> B cave_trk (time-based trigger, >= 900 ms retry gate)"),
    "f7fec": ("N2-10", "CNaviModule::MapMatch: flush when RG service ends -> B cave_flush (>= 900 ms retry gate)"),
    "f8c38": ("N2-10", "WriteRouteTrackFile: loop setup -> BL cave_wrinit (step ~3 s worth of entries), NOP"),
    "f8c48": ("N2-10", "WriteRouteTrackFile: SUB W9,W9,#3 -> SUB W9,W9,W28 (step)"),
    "f8cf4": ("N2-10", "WriteRouteTrackFile: CMP W9,#2 / ADD W10,W10,#3 -> CMP W9,W25 / ADD W10,W10,W28"),
    "f8d5c": ("N2-10", "WriteRouteTrackFile: STR WZR,[X20,#0x3E0] -> B cave_wrreset (also clears ms accumulator)"),
    "109674": ("N2-1", "ICalcMapMatching: tunnel speed hold ADD -> B cave_smooth (halving once per accumulated 1000 ms)"),
    "10967c": ("N2-1", "ICalcMapMatching: LSR W8,W8,#1 -> NOP (moved into cave_smooth)"),
    "10976c": ("N2-1", "ICalcMapMatching: MOV W3,#1000 -> BL stub_w3 (virtual GPS step = w ms)"),
    "109b98": ("N2-1", "MakeVirtualGPS: speed ramp cap 10 -> max(1, w/100) km/h per fix; BL stub_ramp, NOP"),
    "109dd0": ("N2-1", "MakeVirtualGPS: seconds += step/1000 -> new_ms/1000 - old_ms/1000 (BL stub_secs)"),
    "10e400": ("N2-5", "NcRouteMatchEX::SetGpsParsedData: int-truncated >=2 m odometer -> B cave_odo (rate gate + fractional carry)"),
    "10f7b8": ("N2-3", "NcRouteMatchEX::MapMatching: highway counter +1 cap 300 -> +w cap 300000 (B cave_hwinc)"),
    "10f7f0": ("N2-2", "NcRouteMatchEX::MapMatching: off-route counter +1 -> +w (B cave_off1)"),
    "10f868": ("N2-2", "NcRouteMatchEX::MapMatching: off-route counter +2 -> +2w (B cave_off2)"),
    "10f878": ("N2-2", "NcRouteMatchEX::MapMatching: CMP W8,#4 -> CMP W8,#4000"),
    "10f880": ("N2-2", "NcRouteMatchEX::MapMatching: CMP W8,#3 -> CMP W8,#3999"),
    "10fb74": ("N2-4", "NcRouteMatchEX::MapMatching: shadow-mode confirm (<=9 m per fix, 10 fixes) -> B cave_shade (d*100<w, 10000 ms)"),
    "110994": ("N2-3", "NcRouteMatchEX::CheckHighwayDrivingException -> B cave_hde (31000 ms, -5w / -(35-v)w)"),
    "1336dc": ("N2-7", "CSafeDriveInfomation::GetSDIInfo: mode-change debounce +1 / CMP #1 -> +w / CMP #1000"),
    "133fdc": ("N2-7", "CSafeDriveInfomation::GetSDIInfo: section-end grace +1 / CMP #2 -> +w / CMP #2000"),
    "139448": ("N2-9", "SectionSpeedMonitor::Update: BL SavePersistentState -> BL cave_save (>= 900 ms apart)"),
    "1427e4": ("N2-9", "SpeedCalculator::Update: INFO log (initial/shaded) -> BL cave_log1 (>= 900 ms apart)"),
    "142850": ("N2-9", "SpeedCalculator::Update: INFO log (Update: totalDist) -> BL cave_log2 (>= 900 ms apart)"),
    "cave": ("CAVE", "code cave over CRGServiceConfig::FileWriteDefaultConfig @0x15956c (no callers, 2680 B; 1072 B used)"),
}
patches = []
for b in blocks:
    pid, desc = DESC[b["label"]]
    o = b["offset"]
    assert orig[o:o + len(b["new"]) // 2].hex() == b["orig"]
    patches.append({"id": pid, "offset": o, "orig": b["orig"], "new": b["new"], "desc": desc})
# ELF: grow PT_LOAD[3] (.data/.bss) memsz by 0x58 for the slot at VA 0x1e8050; keep .bss sh_size consistent.
SLOT_SIZE = 0x58
memsz_off = 0x40 + 3 * 56 + 0x28
old = struct.unpack_from("<Q", orig, memsz_off)[0]
assert old == 0x1A7A8
patches.append({"id": "SLOT", "offset": memsz_off, "orig": orig[memsz_off:memsz_off + 8].hex(),
                "new": struct.pack("<Q", old + SLOT_SIZE).hex(),
                "desc": "PT_LOAD[3] p_memsz 0x1a7a8 -> 0x1a800 (zeroed slot 0x58 B at VA 0x1e8050, same 4 KB page)"})
shsz_off = 0x1D7FB8 + 24 * 64 + 0x20
old = struct.unpack_from("<Q", orig, shsz_off)[0]
assert old == 0x8278
patches.append({"id": "SLOT", "offset": shsz_off, "orig": orig[shsz_off:shsz_off + 8].hex(),
                "new": struct.pack("<Q", old + SLOT_SIZE).hex(),
                "desc": ".bss sh_size 0x8278 -> 0x82d0 (section header only, cosmetic)"})
patches.sort(key=lambda p: p["offset"])
out = bytearray(orig)
for p in patches:
    n = bytes.fromhex(p["new"]); out[p["offset"]:p["offset"] + len(n)] = n
doc = {
    "target": "lib/arm64-v8a/libNavigationSDK.so (split_config.arm64_v8a.apk)",
    "app": "com.skt.tmap.ku 11.8.4.4075 (versionCode 4004)",
    "design": "time-weighted fix counters; see docs/tmap/N2_patch.md",
    "sha256_in": hashlib.sha256(orig).hexdigest(),
    "sha256_out": hashlib.sha256(out).hexdigest(),
    "size": len(orig),
    "slot": {"va": "0x1e8050", "size": SLOT_SIZE, "fields": {
        "0x00": "int64 last fix time ms (CNaviModule+0x2A8)", "0x08": "int32 w ms (1..1000)",
        "0x0c": "int32 tunnel smoothing accumulator", "0x10": "double odometer fraction total",
        "0x18": "double odometer fraction on-route", "0x20": "reserved", "0x28": "reserved",
        "0x30": "int64 last SavePersistentState", "0x38": "int64 last log1", "0x40": "int64 last log2",
        "0x48": "int32 route-track ms accumulator", "0x50": "int64 last route-track attempt"}},
    "patches": patches,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="\n") as f:
    json.dump(doc, f, indent=1)
    f.write("\n")
print(len(patches), doc["sha256_out"])
