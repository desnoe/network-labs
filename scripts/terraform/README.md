# Terraform

This [Terraform](https://learn.hashicorp.com/terraform) script allow popping up a fresh GNS3/NetBox server for labs on
AWS. It uses a spot instance to lower the cost.

## TL;DR

⚠️ Read and adapt Terraform scripts to your environement!!! ⚠️

Make sure you have AWS credentials somewhere that Packer/Terrafor can rely on (for instance in environment vars).

Run the Terraform script to run the GNS3/NetBox server:

```
cd ./scripts/terraform
terraform plan
terraform apply
```

We can then connect to the [WebUI of the GNS3 server](http://gns3.lab.aws.delarche.fr:3080), or to
the [WebUI of NetBox](http://gns3.lab.aws.delarche.fr:8080),or even directly to
the [NetBox postgres database](postgres://netbox:J5brHrAXFLQSif0K@gns3.lab.aws.delarche.fr/netbox).

To clean-up:

```
terraform destroy
```

## Running the GNS3/NetBox server on a bare-metal instance

By default, Terraform will pop a `t3.small` instance. Since GNS3 runs on top of the KVM-QEMU hypervisor, it won't let
you, by default, run any image requiring this hypervisor, because this type of instance is already a virtual machine
that does not allow nested hypervision. These instances are cheap and are great for simple tests, but if your really
need to run GNS3, then go for a `c5.metal`.

This can be done easily by overloading the variable `gns3_instance_type`:

```
terraform apply -var="gns3_instance_type=c5.metal"
```

## SSH config

Here is configuration pattern you can use in your `~/.ssh/config`:

```
Host gns3
  HostName gns3.lab.aws.delarche.fr
  IdentityFile ~/.ssh/id_rsa
  User ubuntu
  Port 22
  StrictHostKeyChecking no
  UserKnownHostsFile=/dev/null
```