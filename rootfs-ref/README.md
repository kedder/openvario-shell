# Sample filesystem of Openvario device (reference)

This directory tree represents Openvario root filesystem tree. It is used as a
working directory of openvario-shell when it is run in simulation mode.
Normally, in order to run `ovshell` outside of actual OpenVario OS (e.g. on
your laptop), you make a copy of this directory with `make reset-rootfs` and
then run `ovshell` in simulation mode:

```sh
make reset-rootfs
ovshell --sim=var/rootfs
```
