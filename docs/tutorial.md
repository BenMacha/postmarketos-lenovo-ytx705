# Installing postmarketOS on the Lenovo Yoga Smart Tab (YT-X705)

Tested on a YT-X705L (Android 10, build `S001136_220811_ROW`). This **erases the tablet**.
Commands run on a computer with `adb`/`fastboot` (Android platform-tools); the image
build needs a Linux machine (pmbootstrap does not run on macOS).

## 1. Unlock the bootloader

1. Android settings → About → tap *Build number* 7 times; Developer options → enable
   **OEM unlocking** and **USB debugging**.
2. Unlock (this wipes all data):

   ```sh
   adb reboot bootloader
   fastboot oem unlock-go      # "fastboot flashing unlock" is refused on this tablet
   ```

The tablet reboots, wipes itself and comes back to Android (boot state `orange`).

## 2. Build lk2nd

lk2nd's own DTBs are rejected by this aboot, so it is repacked with the stock base DTB.

```sh
git clone https://github.com/msm8916-mainline/lk2nd && cd lk2nd
make TOOLCHAIN_PREFIX=arm-none-eabi- LK2ND_QCDTBS= lk2nd-msm8952
```

You need the stock base DTB. It is identical on Android 9 and 10: take it from the stock
kernel and dtbo published in the TWRP tree (or later from your own `boot.img`, step 3):

```sh
T=https://raw.githubusercontent.com/burn-sie/twrp_device_lenovo_YTX705/android-9.0/prebuilt
curl -LO $T/Image.gz-dtb -LO $T/dtbo.img
tools/extract-stock-dt.py Image.gz-dtb dtbo.img stock/    # writes stock/base.dtb
tools/lk2nd-stock-dtb.py build-lk2nd-msm8952/lk2nd.img build-lk2nd-msm8952/lk.bin \
    stock/base.dtb lk2nd-ytx705.img
```

## 3. Try lk2nd and back up the tablet

Power off, then hold **Volume down + Power** to reach fastboot.

```sh
fastboot boot lk2nd-ytx705.img          # runs from RAM, writes nothing
fastboot getvar all | grep lk2nd        # lk2nd:compatible:lenovo,ytx705
```

If the aboot answers `unknown reason`, run `fastboot reboot bootloader` and retry.

Back up the stock partitions (keep them private: IMEI, serial, calibration):

```sh
mkdir backup && cd backup
for p in dtbo recovery vbmeta aboot persist modem fsg modemst1 modemst2 dsp splash; do
  fastboot fetch $p $p.img
done
fastboot fetch lk2nd head.img && fastboot fetch boot tail.img && cat head.img tail.img > boot.img
rm head.img tail.img
```

## 4. Build the postmarketOS image (Linux machine)

```sh
git clone --depth 1 https://gitlab.postmarketos.org/postmarketOS/pmbootstrap.git
pmbootstrap/pmbootstrap.py init     # vendor qcom, device msm89x7, UI plasma-mobile
```

Add the kernel patches to the kernel package, then build:

```sh
K=$(pmbootstrap/pmbootstrap.py config aports)/device/testing/linux-postmarketos-qcom-msm89x7
cp kernel/*.patch $K/
# add the patch file names to source= in $K/APKBUILD (in order), then:
pmbootstrap/pmbootstrap.py checksum linux-postmarketos-qcom-msm89x7
pmbootstrap/pmbootstrap.py build --force linux-postmarketos-qcom-msm89x7
pmbootstrap/pmbootstrap.py install --password <your password>
```

The image is `<work>/chroot_native/home/pmos/rootfs/qcom-msm89x7.img`. Convert it to a
sparse image so fastboot sends less data:

```sh
img2simg qcom-msm89x7.img pmos-userdata.simg      # android-sdk-libsparse-utils
```

### Optional: test the kernel from RAM first

Build a boot image with the kernel, the DTB and the initramfs from the image's `/boot`, then
boot it from lk2nd; the initramfs opens a debug shell (`telnet 172.16.42.1`):

```sh
cat vmlinuz sdm439-lenovo-ytx705.dtb > vmlinuz-dtb
mkbootimg --kernel vmlinuz-dtb --ramdisk initramfs --base 0x80000000 --kernel_offset 0x8000 \
  --ramdisk_offset 0x1000000 --tags_offset 0x100 --pagesize 2048 \
  --cmdline "console=tty0 pmos.debug-shell" -o boot-ramtest.img
fastboot boot lk2nd-ytx705.img     # from the Lenovo fastboot
fastboot boot boot-ramtest.img     # from lk2nd's fastboot
```

## 5. Flash

From the Lenovo fastboot (Volume down + Power):

```sh
fastboot flash boot lk2nd-ytx705.img
fastboot flash userdata pmos-userdata.simg
fastboot reboot
```

lk2nd finds postmarketOS on `userdata` and boots it. The Plasma Mobile lock screen PIN is
the password given to `pmbootstrap install`. Over USB, the tablet is reachable at
`ssh user@172.16.42.1`.

## 6. After the first boot

**Pin the kernel.** The postmarketOS repository has its own
`linux-postmarketos-qcom-msm89x7` without the YT-X705 device tree; if an upgrade replaced
yours, lk2nd would find no DTB and the tablet would not boot:

```sh
sudo apk add linux-postmarketos-qcom-msm89x7=7.1.3-r11    # use your built version
```

To update the kernel, copy your newer package and `sudo apk add --allow-untrusted
linux-postmarketos-qcom-msm89x7-<version>.apk`, then change the pin.

**French interface:**

```sh
printf '[Formats]\nLANG=fr_FR.UTF-8\n\n[Translations]\nLANGUAGE=fr\n' > ~/.config/plasma-localerc
```

Installing a local `.apk` file pins it by checksum in `/etc/apk/world`, which also keeps it.
After every kernel install, reboot to test it.

**Faster UI** (software rendering until the DSI/GPU work is done): Settings → Workspace
behaviour → animation speed: instant.

## Going back to Android

From the Lenovo fastboot, flash the saved `boot.img` (and `dtbo`, `recovery`, `vbmeta` if
you changed them), then `fastboot erase userdata` and reboot. Lenovo's *Rescue and Smart
Assistant* (Windows) can also reinstall the full stock firmware.
