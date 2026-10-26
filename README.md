# postmarketOS on the Lenovo Yoga Smart Tab (YT-X705F/L/X)

Work in progress port of mainline Linux / [postmarketOS](https://postmarketos.org) to the
**Lenovo Yoga Smart Tab** (2019, Qualcomm SDM439, 10.1" 1200×1920), built on the
[msm89x7-mainline](https://github.com/msm89x7-mainline/linux) kernel and the generic
`qcom-msm89x7` postmarketOS device. Target UI: Plasma Mobile.

> 🇫🇷 postmarketOS (Plasma Mobile) démarre sur la Lenovo Yoga Smart Tab.
> Tutoriel complet en français : [docs/fr.md](docs/fr.md).

**Step-by-step guide: [docs/tutorial.md](docs/tutorial.md).**

## Status

| Part | State |
|---|---|
| Bootloader unlock | ✅ `fastboot oem unlock-go` (wipes data) |
| lk2nd | ✅ flashed to `boot`, with the stock base DTB, see below |
| Mainline kernel 7.1.3 + DTS | ✅ boots ([kernel/](kernel/)) |
| postmarketOS + Plasma Mobile | ✅ boots from `userdata`, lock screen and shell work |
| Display | ✅ `simpledrm` (bootloader splash, 1200×1920) — software rendering, slow |
| DSI panel + GPU | 🚧 drivers in place but disabled in the DTS: the 12nm DSI PLL does not lock (see below) |
| Touchscreen | ✅ FocalTech FT8201 (`focaltech,ft8201`, `edt-ft5x06`), axes inverted (panel mounted upside down) |
| Buttons | ✅ power, volume up/down |
| eMMC, µSD, USB networking | ✅ |
| Wi-Fi | ✅ WCNSS (Pronto) + WCN3660B, firmware loaded from the modem partition |
| Bluetooth | 🧪 driver loads, not tested |
| French UI | ✅ set `[Translations] LANGUAGE=fr` in `~/.config/plasma-localerc` |
| Audio, battery, sensors (auto-rotation), cameras | ❓ to do |

## Kernel patches

On top of msm89x7-mainline 7.1.3 ([kernel/](kernel/)):

1. `arm64: dts: qcom: sdm439: Add Lenovo Yoga Smart Tab (YT-X705)`
2. `drm/msm/dsi: Add simple 12nm PHY/PLL driver` — by Lanik, from msm89x7-mainline
   `barni2000/6.14-sdm439`, forward-ported
3. `drm/panel: Add Lenovo YT-X705 FT8201 BOE panel` — generated with
   linux-mdss-dsi-panel-driver-generator; DSI/GPU nodes described, `status = "disabled"`
4. `drm/msm/dsi: dsi_phy_12nm: Use determine_rate` — 7.1 dropped `clk_ops.round_rate`
5. `soc: qcom: ubwc: Add SDM429 and SDM439` — without it `msm-mdss` fails with `-EINVAL`
   (`Couldn't find UBWC config data for this platform`)

### Display status (help welcome)

With `mdss`/`gpu` enabled (DSI `vdda` = PM8953 L23, `vddio` = L6, PHY in LDO mode, as in
the stock DT), the DRM device and the panel probe, but `DSI PLL is *not* locked` and
`dsi_link_clk_set_rate_6g: Failed to set rate pixel clk, -22`, then vblank timeouts.
Note: a failed `msm-mdss` probe also turns off the bootloader framebuffer (black screen).

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
- The touchscreen reports coordinates rotated by 180° compared to the bootloader
  framebuffer: the DTS sets `touchscreen-inverted-x` and `touchscreen-inverted-y`.

## Building postmarketOS

The kernel patch goes into the `linux-postmarketos-qcom-msm89x7` package of pmaports
(don't use `pmbootstrap build --src`: its copy follows `.gitignore` and drops
`kernel/time/timeconst.bc`, so the build fails). Full commands in
[docs/tutorial.md](docs/tutorial.md).

## Credits

- msm89x7-mainline, msm8916-mainline (lk2nd) and postmarketOS contributors.
- The DTS starts from `sdm429-lenovo-tbx505x.dts` (Lenovo Tab M10 HD) by Kaustabh Chakraborty.
- Stock kernel/DTB reference: [burn-sie/twrp_device_lenovo_YTX705](https://github.com/burn-sie/twrp_device_lenovo_YTX705).

## License

Kernel and lk2nd files keep their upstream licenses (GPL-2.0 / BSD-3-Clause, see SPDX
headers). The tools and docs of this repository are MIT.
