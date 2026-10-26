#!/usr/bin/env python3
"""Repack lk2nd with the stock base DTB of the Yoga Smart Tab.

The YT-X705 aboot rejects lk2nd's own small DTBs ("dtb not found") even
with the right qcom,msm-id/qcom,pmic-id, but accepts the stock SDM439 MTP
base DTB. This tool takes a built lk2nd.img (msm8952 target, built with
LK2ND_QCDTBS= so it has no QCDT table), replaces its appended DTBs with the
stock base DTB plus an /lk2nd node, and writes a bootable image.

Usage:
    lk2nd-stock-dtb.py lk2nd.img lk.bin base.dtb OUT.img

lk.bin is build-lk2nd-msm8952/lk.bin (the binary without appended DTBs).
Test with `fastboot boot OUT.img` first; nothing is written to the device.
"""
import os
import struct
import subprocess
import sys
import tempfile

LK2ND_NODE = """\
	lk2nd {
		model = "Lenovo Yoga Smart Tab";
		compatible = "lenovo,ytx705";
		lk2nd,dtb-files = "sdm439-lenovo-ytx705";
	};
"""


def add_lk2nd_node(base_dtb):
    dts = subprocess.run(["dtc", "-q", "-I", "dtb", "-O", "dts", base_dtb],
                         capture_output=True, check=True).stdout.decode()
    anchor = dts.index("\tcpus {")
    dts = dts[:anchor] + LK2ND_NODE + dts[anchor:]
    with tempfile.NamedTemporaryFile("w", suffix=".dts", delete=False) as f:
        f.write(dts)
        path = f.name
    try:
        return subprocess.run(["dtc", "-q", "-I", "dts", "-O", "dtb", path],
                              capture_output=True, check=True).stdout
    finally:
        os.unlink(path)


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    ref_img, lk_bin, base_dtb, out = sys.argv[1:]
    with open(ref_img, "rb") as f:
        ref = f.read()
    if ref[:8] != b"ANDROID!":
        raise SystemExit("lk2nd.img: not an Android boot image")
    page, = struct.unpack("<I", ref[36:40])
    kernel_size, = struct.unpack("<I", ref[8:12])
    ramdisk_size, = struct.unpack("<I", ref[16:20])
    dt_size, = struct.unpack("<I", ref[40:44])
    if dt_size:
        raise SystemExit("lk2nd.img has a QCDT table: rebuild with LK2ND_QCDTBS=")
    ramdisk_off = page + -(-kernel_size // page) * page
    ramdisk = ref[ramdisk_off:ramdisk_off + ramdisk_size]

    with open(lk_bin, "rb") as f:
        kernel = f.read() + add_lk2nd_node(base_dtb)
    header = bytearray(ref[:page])
    struct.pack_into("<I", header, 8, len(kernel))

    def pad(b):
        return b + b"\0" * (-len(b) % page)

    with open(out, "wb") as f:
        f.write(bytes(header) + pad(kernel) + pad(ramdisk))
    print(f"{out}: lk2nd {len(kernel)} bytes (with stock DTB)")


if __name__ == "__main__":
    main()
