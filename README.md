# postmarketOS on the Lenovo Yoga Smart Tab (YT-X705F/L/X)

Work in progress port of mainline Linux / [postmarketOS](https://postmarketos.org) to the
**Lenovo Yoga Smart Tab** (2019, Qualcomm SDM439, 10.1" 1200×1920), built on the
[msm89x7-mainline](https://github.com/msm89x7-mainline/linux) kernel and the generic
`qcom-msm89x7` postmarketOS device. Target UI: Plasma Mobile.

> 🇫🇷 Portage en cours de Linux mainline / postmarketOS sur la Lenovo Yoga Smart Tab.
> Le bootloader se déverrouille, lk2nd démarre ; le noyau et l'image sont en cours de test.
> Voir [docs/fr.md](docs/fr.md).

## Status

| Part | State |
|---|---|
| Bootloader unlock | ✅ `fastboot oem unlock-go` (wipes data) |
| lk2nd | ✅ boots from RAM (`fastboot boot`) with the stock base DTB, see below |
| Mainline DTS | 🧪 written ([kernel/](kernel/)), not booted yet |
| Display | 🧪 `simple-framebuffer` from the bootloader splash (no DSI panel driver yet) |
| Touchscreen | 🧪 FocalTech FT8201 (`focaltech,ft8201`, `edt-ft5x06`), I²C 3 @ 0x38 |
| Wi-Fi / BT | 🧪 WCNSS (Pronto) + WCN3660B, same wiring as the TB-X505X |
| Audio, battery, cameras, GPU | ❓ not looked at yet |

## Hardware (from the stock device tree)

- SoC: SDM439 (`soc_id` 353), platform `MTP`, subtype 1, PMICs PM8953 + PMI632.
- Panel: `qcom,mdss_dsi_boe_ft8201_1200p_video` — BOE panel with FocalTech FT8201 TDDI,
  4 lanes, video mode, DCS backlight (12 bit), reset GPIO 60, power GPIO 17, TE GPIO 24,
  backlight enable on PM8953 GPIO 4, supplies `vddio` (L6), `lab`/`ibb` (PMI632 LCDB).
- Touch: I²C 3 (`0x78b7000`) @ 0x38, IRQ GPIO 65, reset GPIO 64.
- Keys: Volume Up GPIO 91, Volume Down = PM8953 RESIN, Power = PM8953 PON.
- µSD card detect: GPIO 67.

## Booting lk2nd

The YT-X705 aboot refuses the small DTBs that lk2nd normally appends (`dtb not found`),
even with the stock `qcom,msm-id <0x161 0>` / `qcom,pmic-id <0x10016 0x25 0 0>`.
It does accept the **stock SDM439 MTP base DTB**: the stock base DTB has no
`qcom,board-id`, the board data (`<8 1>`) comes from the `dtbo` partition overlay,
which the aboot applies on top. So lk2nd is repacked with the stock base DTB plus an
`/lk2nd` node:

```sh
# 1. build lk2nd (msm8952 target) without its QCDT table
make TOOLCHAIN_PREFIX=arm-none-eabi- LK2ND_QCDTBS= lk2nd-msm8952
# 2. extract the stock base DTB from your own boot.img + dtbo.img
tools/extract-stock-dt.py boot.img dtbo.img stock/
# 3. replace lk2nd's DTBs with it
tools/lk2nd-stock-dtb.py build-lk2nd-msm8952/lk2nd.img build-lk2nd-msm8952/lk.bin stock/base.dtb lk2nd-ytx705.img
# 4. try it from RAM — nothing is written
fastboot boot lk2nd-ytx705.img
```

`fastboot getvar all` then answers `product:lk2nd-msm8952`, `lk2nd:compatible:lenovo,ytx705`.
[lk2nd/sdm439-lenovo-ytx705.dts](lk2nd/sdm439-lenovo-ytx705.dts) is the regular lk2nd
entry, kept for when the root cause is understood.

### Getting your stock boot.img without a firmware download

Once lk2nd runs, it can read partitions: `fastboot fetch dtbo dtbo.img`, etc.
`boot` is special: lk2nd hides its first 512 KiB as a pseudo partition `lk2nd`, so
fetch both and concatenate:

```sh
fastboot fetch lk2nd head.img && fastboot fetch boot tail.img && cat head.img tail.img > boot.img
```

Back up at least `boot dtbo recovery vbmeta modem persist modemst1 modemst2 fsg` before
flashing anything. **Never publish them**: they hold your IMEI, serial number and
calibration data.

## Pitfalls

- `fastboot flashing unlock` answers `Need wipe userdata. Do 'fastboot oem unlock-go'`.
- After one failed `fastboot boot`, the aboot answers `unknown reason` to everything until
  `fastboot reboot bootloader`. Restart it between tests.
- `fastboot getvar <name>` hangs on the stock aboot; `fastboot getvar all` works.

## Building postmarketOS

```sh
pmbootstrap init                      # device: qcom-msm89x7, UI: plasma-mobile
git -C linux am ../kernel/*.patch     # on top of msm89x7-mainline 7.1.3
pmbootstrap build --force --src=linux linux-postmarketos-qcom-msm89x7
pmbootstrap install
```

## Credits

- msm89x7-mainline, msm8916-mainline (lk2nd) and postmarketOS contributors.
- The DTS starts from `sdm429-lenovo-tbx505x.dts` (Lenovo Tab M10 HD) by Kaustabh Chakraborty.
- Stock kernel/DTB reference: [burn-sie/twrp_device_lenovo_YTX705](https://github.com/burn-sie/twrp_device_lenovo_YTX705).

## License

Kernel and lk2nd files keep their upstream licenses (GPL-2.0 / BSD-3-Clause, see SPDX
headers). The tools and docs of this repository are MIT.
