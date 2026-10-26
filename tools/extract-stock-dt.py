#!/usr/bin/env python3
"""Extract the stock device tree of the Lenovo Yoga Smart Tab (YT-X705).

The stock boot image carries ~20 generic Qualcomm DTBs appended to the
kernel; the bootloader picks one by qcom,msm-id + qcom,pmic-id (the base
DTB has no qcom,board-id), then applies the board overlay from the dtbo
partition whose qcom,board-id matches the hardware.

Usage:
    extract-stock-dt.py boot.img dtbo.img OUTDIR [--model "SDM439 MTP"] [--board-id 8,1]

boot.img may also be a bare Image.gz-dtb (kernel with appended DTBs).

Writes OUTDIR/base.dtb, OUTDIR/overlay.dtbo and, when fdtoverlay and dtc
are installed, OUTDIR/merged.dtb + OUTDIR/merged.dts.
"""
import argparse
import os
import shutil
import struct
import subprocess

FDT_MAGIC = b"\xd0\x0d\xfe\xed"
DTBO_MAGIC = 0xD7B7AB1E


def appended_dtbs(boot):
    """DTBs appended to the kernel of a boot.img, or of a bare Image.gz-dtb."""
    if boot[:8] == b"ANDROID!":
        kernel_size, = struct.unpack("<I", boot[8:12])
        page_size, = struct.unpack("<I", boot[36:40])
        kernel = boot[page_size:page_size + kernel_size]
    else:
        kernel = boot
    i = 0
    while True:
        i = kernel.find(FDT_MAGIC, i)
        if i < 0:
            return
        size = int.from_bytes(kernel[i + 4:i + 8], "big")
        if 0x100 < size < 0x400000:
            yield kernel[i:i + size]
            i += size
        else:
            i += 4


def dtbo_entries(dtbo):
    magic, _total, _hdr, entry_size, count, offset = struct.unpack(">6I", dtbo[:24])
    if magic != DTBO_MAGIC:
        raise SystemExit("dtbo.img: bad magic")
    for n in range(count):
        size, off = struct.unpack(">2I", dtbo[offset + n * entry_size:offset + n * entry_size + 8])
        yield dtbo[off:off + size]


def board_id(blob):
    """Return the first qcom,board-id pair of a DTB/DTBO, or None (via dtc)."""
    dts = subprocess.run(["dtc", "-q", "-I", "dtb", "-O", "dts", "-"], input=blob,
                         capture_output=True).stdout.decode(errors="replace")
    for line in dts.splitlines():
        line = line.strip()
        if line.startswith("qcom,board-id"):
            cells = line.split("<", 1)[1].split(">", 1)[0].split()
            return tuple(int(c, 0) for c in cells[:2])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("boot")
    ap.add_argument("dtbo")
    ap.add_argument("outdir")
    ap.add_argument("--model", default="SDM439 MTP")
    ap.add_argument("--board-id", default="8,1", help="platform type,subtype (MTP=8)")
    args = ap.parse_args()
    want = tuple(int(x, 0) for x in args.board_id.split(","))
    os.makedirs(args.outdir, exist_ok=True)

    with open(args.boot, "rb") as f:
        boot = f.read()
    base = next((d for d in appended_dtbs(boot) if args.model.encode() in d), None)
    if base is None:
        raise SystemExit(f"no appended DTB with model containing {args.model!r}")
    with open(os.path.join(args.outdir, "base.dtb"), "wb") as f:
        f.write(base)
    print(f"base.dtb: {len(base)} bytes")

    if not shutil.which("dtc"):
        raise SystemExit("dtc is needed to pick the overlay (install device-tree-compiler)")
    with open(args.dtbo, "rb") as f:
        dtbo = f.read()
    overlay = next((o for o in dtbo_entries(dtbo) if board_id(o) == want), None)
    if overlay is None:
        raise SystemExit(f"no dtbo entry with qcom,board-id {want}")
    with open(os.path.join(args.outdir, "overlay.dtbo"), "wb") as f:
        f.write(overlay)
    print(f"overlay.dtbo: board-id {want}, {len(overlay)} bytes")

    if shutil.which("fdtoverlay"):
        merged = os.path.join(args.outdir, "merged.dtb")
        subprocess.run(["fdtoverlay", "-i", os.path.join(args.outdir, "base.dtb"),
                        "-o", merged, os.path.join(args.outdir, "overlay.dtbo")], check=True)
        subprocess.run(["dtc", "-q", "-s", "-I", "dtb", "-O", "dts", merged,
                        "-o", os.path.join(args.outdir, "merged.dts")], check=True)
        print("merged.dts written")


if __name__ == "__main__":
    main()
