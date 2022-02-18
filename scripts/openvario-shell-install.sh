#!/bin/sh
# Installation script for openvario-shell.
#
# Run it on your openvario-device to replace the original menu system with
# openvario-shell

FEED_FILENAME="/etc/opkg/customfeeds.conf"

grep -q "kedder_core" $FEED_FILENAME
if [[ $? != 0 ]]; then
    echo Installing opkg feeds to $FEED_FILENAME...
    echo src/gz kedder_core http://openvario.lebedev.lt/opkg/cortexa7t2hf-neon/ -neon >> $FEED_FILENAME
    echo src/gz kedder_all http://openvario.lebedev.lt/opkg/all >> $FEED_FILENAME
fi

echo Installing openvario-shell

opkg update
set -e
opkg install openvario-shell openvario-shell-autostart --force-removal-of-dependent-packages

echo
echo
echo openvario-shell is installed. Reboot your device.
