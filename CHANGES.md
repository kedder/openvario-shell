Changelog for openvario-shell
=============================

0.7.2 (2021-03-24)
------------------

- Connman: fix crash when incomplete service object arrives from DBUS.


0.7.1 (2021-03-21)
------------------

- Connman: fix exception when signal strength is missing from a service 
  property (likely to happen when connected to ethernet).


0.7.0 (2021-03-07)
------------------

- Implement a new "Networking" app: connect to WiFi networks and more
- Avoid error in backup app when rsync produces a lot of unexpected output.


0.6.1 (2020-08-23)
------------------

- Correctly determine version of variod.


0.6 (2020-08-23)
----------------

- Backup app: transfer files between USB stick and Openvario.
- Initial setup app: wizard to pick device orientation, calibrate touch screen and
  sensors.
- About app: display system information.
- Flush filesystem caches before shutting down.


0.5.1 (2020-06-30)
------------------

- Correct the path to /bin/date executable.
- Sync filesystems after XCSoar exits to avoid data loss on sudden power-off.


0.5 (2020-06-27)
----------------

- Ability to read NMEA stream from connected serial devices, with baud rate
  autodetection. Display detected devices on top bar.
- System upgrade app. Fetch packages from opkg sources (internet or locally
  mounted USB stick), allow to pick packages to upgrade.
- Automatically set system date and time from GPS source (if system time is
  found to be out-of-sync). Show system time on top bar. Red indicator turns
  black when current time is detected in GPS NMEA stream.
- Clear the screen when exiting to shell


0.4 (2020-05-15)
----------------

- Log downloader app. Supports downloading `*.igc` as well as `*.nmea` files.
- Autostart chosen application when openvario shell is started. Application and
  timeout is configurable in settings.
- More languages for XCSoar to choose from

0.3 (2020-04-30)
----------------

- Initial API to support 3rd party apps.
- Do not write to xcsoar profile on startup if no changes are made.
- Add more language choices for XCSoar.


0.2 (2020-04-20)
----------------

- Initial release
