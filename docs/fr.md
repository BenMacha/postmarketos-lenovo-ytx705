# Linux sur la Lenovo Yoga Smart Tab — résumé en français

Ce dépôt suit le portage de postmarketOS (Linux mainline, interface Plasma Mobile) sur la
Lenovo Yoga Smart Tab (YT-X705F/L/X).

## Où on en est

- Le bootloader se déverrouille avec `fastboot oem unlock-go` (efface les données).
- lk2nd démarre en mémoire (`fastboot boot`), sans rien écrire, à condition d'y mettre le
  device tree d'origine (voir le README, section « Booting lk2nd »).
- Le device tree mainline est écrit ; le premier démarrage du noyau est en cours de test.

## Avant de commencer

1. Sauvegardez vos partitions avec lk2nd (`fastboot fetch …`, voir le README).
   Ne les publiez jamais : elles contiennent l'IMEI, le numéro de série et la calibration.
2. Testez toujours avec `fastboot boot` avant tout `fastboot flash`.
3. Pour revenir à Android : reflashez `boot`, `dtbo`, `recovery` et `vbmeta` sauvegardés,
   ou utilisez l'outil officiel Lenovo Rescue and Smart Assistant.
