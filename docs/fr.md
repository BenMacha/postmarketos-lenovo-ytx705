# Installer Linux (postmarketOS) sur la Lenovo Yoga Smart Tab — tutoriel

Testé sur une YT-X705L (Android 10, version `S001136_220811_ROW`). **La tablette est
entièrement effacée.** Les commandes se lancent depuis un ordinateur avec `adb`/`fastboot` ;
la fabrication de l'image demande une machine Linux (pmbootstrap ne tourne pas sous macOS).
Les commandes détaillées sont dans le tutoriel anglais : [tutorial.md](tutorial.md).

## Où en est le portage

| Élément | État |
|---|---|
| Déverrouillage, lk2nd | ✅ |
| Noyau Linux 7.1.3 + Plasma Mobile | ✅ démarre, écran de verrouillage et shell |
| Écran | ✅ mais affichage logiciel (lent) : pas encore de pilote d'écran DSI ni de GPU |
| Tactile, boutons, eMMC, carte µSD, réseau USB | ✅ |
| Wi-Fi, Bluetooth | 🧪 décrits, pas encore testés |
| GPU, son, batterie, caméras | ❓ à faire |

## Les étapes

1. **Déverrouiller** : Options pour les développeurs → *Déverrouillage OEM* et *Débogage
   USB*, puis `adb reboot bootloader` et `fastboot oem unlock-go` (Lenovo refuse
   `fastboot flashing unlock`). La tablette s'efface et redémarre sous Android.
2. **Préparer lk2nd** avec le device tree d'origine (`tools/lk2nd-stock-dtb.py`) :
   le bootloader Lenovo refuse les device trees fournis par lk2nd.
3. **Essayer lk2nd sans rien écrire** : éteindre, *Volume bas + Power* pour le mode
   fastboot, puis `fastboot boot lk2nd-ytx705.img`. Sauvegarder ensuite les partitions
   d'origine avec `fastboot fetch` (voir le tutoriel anglais).
   **Ne jamais publier ces sauvegardes** : elles contiennent l'IMEI, le numéro de série et
   la calibration de la tablette.
4. **Fabriquer l'image** avec pmbootstrap (appareil `qcom-msm89x7`, interface
   `plasma-mobile`), en ajoutant le patch du dossier `kernel/` au paquet du noyau.
5. **Flasher** depuis le mode fastboot Lenovo :

   ```sh
   fastboot flash boot lk2nd-ytx705.img
   fastboot flash userdata pmos-userdata.simg
   fastboot reboot
   ```

6. **Premier démarrage** : le code PIN de l'écran de verrouillage est le mot de passe donné
   à `pmbootstrap install`. Par le câble USB : `ssh user@172.16.42.1`.

## Pièges rencontrés

- Après un `fastboot boot` raté, le bootloader répond `unknown reason` à tout : faire
  `fastboot reboot bootloader` entre deux essais.
- `fastboot getvar <nom>` se bloque ; `fastboot getvar all` fonctionne.
- Avec lk2nd, `fastboot fetch boot` saute les 512 premiers Ko : récupérer aussi la
  pseudo-partition `lk2nd` et les mettre bout à bout.
- L'écran est monté à l'envers : le tactile a besoin de `touchscreen-inverted-x/y`.
- `pmbootstrap build --src` oublie `kernel/time/timeconst.bc` : passer par un patch dans le
  paquet du noyau.

## Revenir à Android

Depuis le mode fastboot Lenovo, reflasher le `boot.img` sauvegardé (et `dtbo`, `recovery`,
`vbmeta` si besoin), puis `fastboot erase userdata` et redémarrer. L'outil Lenovo *Rescue
and Smart Assistant* (Windows) peut aussi réinstaller le firmware d'origine complet.
