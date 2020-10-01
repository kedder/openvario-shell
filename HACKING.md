# Development notes

## Developing a connman client

Connman client uses DBUS for communicating with connman daemon. This makes
developing on laptop a bit problematic, because connman is most probably not
installed on your development machine.

However it is possible to expose DBUS interface on Openvario device (or, for
that matter, any other networked device running connman daemon) to the network.
That in turn will allow to make `ovshell` connect to it over the tcp and allow
to debug the app.

In order to do this, add `/etc/dbus-1/system.d/public-tcp.conf` file on the
device running connman:

```xml
<!DOCTYPE busconfig PUBLIC
 "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
    <listen>tcp:host=localhost,bind=*,port=55556,family=ipv4</listen>
    <listen>unix:tmpdir=/tmp</listen>
    <auth>EXTERNAL</auth>
    <auth>ANONYMOUS</auth>
    <allow_anonymous/>
    <apparmor mode="disabled" />
    <policy context="default">
        <allow user="*" />
        <allow own="*" />
        <allow send_type="*" />
        <allow receive_type="*" />
        <allow send_destination="*"/>
    </policy>
</busconfig>
```

Also, add  this line to `/lib/systemd/system/dbus.socket`:

```
[Listen]
...
ListenStream=55556
```

After rebooting the connman machine, it verify connection by running `d-feet`
app on the development machine. Connect to address like this:

```
tcp:host=<ip>,port=55556
```