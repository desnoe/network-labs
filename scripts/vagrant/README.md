# Vagrant

This [Vagrant](https://learn.hashicorp.com/vagrant) script allow popping up fresh GNS3/NetBox virtual machein for
network labs on your laptop.

## Disclaimer

This script has been tested on Parallels only. It may not work with other backends. Check nested hyperivision
parameters.

⚠️ Always read, understand and adapt Vagrant scripts to your environement!!! ⚠️

## TL;DR

```
cd ./scripts/vagrant
vagrant up
vagrant ssh
```

Check the IP address of the Virtual Machine and add it to your /etc/hosts, e.g. call it gns3.lab.

We can then connect to the [WebUI of the GNS3 server](http://gns3.lab:3080), or to
the [WebUI of NetBox](http://gns3.lab:8080),or even directly to
the [NetBox postgres database](postgres://netbox:J5brHrAXFLQSif0K@gns3.lab/netbox).

To clean-up:

```
vagrant destroy
```

## SSH config

You can get a working SSH configuration to put in your `~/.ssh/config` simply:

## SSH config

Here is configuration pattern you can use in your `~/.ssh/config`:

```
vagrant ssh-config
```
