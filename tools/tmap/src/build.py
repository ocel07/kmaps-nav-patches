import json, re, subprocess, sys, os, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.environ.get("NDK_LLVM_BIN", r"C:\Apps\android-sdk\ndk\29.0.14206865\toolchains\llvm\prebuilt\windows-x86_64\bin")
# original lib/arm64-v8a/libNavigationSDK.so of TMAP 11.8.4.4075: first argument or env TMAP_NAVSDK_SO
SO = sys.argv[1] if len(sys.argv) > 1 else os.environ["TMAP_NAVSDK_SO"]
BASE = 0xF0000

def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr); sys.exit(1)
    return r.stdout

run(os.path.join(BIN, "clang.exe"), "--target=aarch64-linux-android30", "-c", os.path.join(HERE, "patch.s"), "-o", os.path.join(HERE, "patch.o"))
DEFS = ["--defsym=" + l.strip() for l in open(os.path.join(HERE, "defsyms.txt")) if l.strip()]
run(os.path.join(BIN, "ld.lld.exe"), *DEFS, "-static", "--no-pie", "-e", "_start", "--section-start=.text=0x%x" % BASE,
    os.path.join(HERE, "patch.o"), "-o", os.path.join(HERE, "patch.elf"))
syms = {}
for line in run(os.path.join(BIN, "llvm-nm.exe"), os.path.join(HERE, "patch.elf")).splitlines():
    p = line.split()
    if len(p) == 3:
        syms[p[2]] = int(p[0], 16)
# .text contents
hdr = run(os.path.join(BIN, "llvm-readelf.exe"), "-S", os.path.join(HERE, "patch.elf"))
m = re.search(r"\.text\s+PROGBITS\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)", hdr)
va, off, size = (int(x, 16) for x in m.groups())
assert va == BASE
elf = open(os.path.join(HERE, "patch.elf"), "rb").read()
text = elf[off:off + size]
orig = open(SO, "rb").read()
blocks = []
for name, start in sorted(syms.items(), key=lambda kv: kv[1]):
    if not name.startswith("b_"):
        continue
    end = syms["e_" + name[2:]]
    new = text[start - BASE:end - BASE]
    o = start  # file offset == VA in the RX segment
    blocks.append({"offset": o, "orig": orig[o:o + len(new)].hex(), "new": new.hex(), "label": name[2:]})
json.dump({"blocks": blocks, "syms": {k: v for k, v in syms.items()}}, open(os.path.join(HERE, "blocks.json"), "w"), indent=1)
for b in blocks:
    print("%-8s 0x%06x len %4d" % (b["label"], b["offset"], len(b["new"]) // 2))
print("cave end 0x%x (limit 0x159fe4)" % syms["e_cave"])
