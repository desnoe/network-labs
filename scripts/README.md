# Script collection

This folder is a collection of scripts to ease the management of the network labs. It can be divided in 2 kind of scripts: scripts that
ease the management of the GNS3 server and scripts that ease the management of a network lab on the  GNS3 server.

## GNS3 server scripts

- [packer](./packer/README.md) script generates GNS3/Netbox server images to be used with vagrant or on AWS
- [vagrant](./vagrant/README.md) script pops up a GNS3/Netbox virtual machine on your laptop
- [terraform](./terraform/README.md) script pops up a GNS3/Netbox virtual machine on AWS

## GNS3 lab scripts

- [netbox-psql](./netbox-psql/README.md) restore (or dumps) the netbox database used by network labs
- [netbox-to-gns3](./netbox-to-gns3/README.md) generates the lab on the GNS3 server from the data in Netbox