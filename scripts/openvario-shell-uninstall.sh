#!/bin/sh -e
# Uninstall openvario-shell and install the original menu back.
#
# Run it on your openvario-device to replace the original menu system with
# openvario-shell

set -e
echo Replacing openvario-shell with the original Openvario menu
opkg install ovmenu-ng ovmenu-ng-autostart --force-removal-of-dependent-packages

echo
echo openvario-shell is uninstalled. Reboot your device.
