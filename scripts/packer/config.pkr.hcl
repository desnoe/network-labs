packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.2"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

locals {
  timestamp = formatdate("YYYYMMDD", timestamp())
}

source "vagrant" "ubuntu" {
  insert_key   = true
  communicator = "ssh"
  source_path  = "bento/ubuntu-20.04"
  ssh_username = "vagrant"
  ssh_password = "vagrant"
  provider     = "parallels"
  add_force    = true
}

source "amazon-ebs" "ubuntu" {
  ami_name      = "gns3-server-ubuntu-focal-${local.timestamp}"
  instance_type = "t3.small"
  region        = "eu-west-3"
  profile       = "dev"

  source_ami_filter {
    filters     = {
      name                = "ubuntu/images/*ubuntu-focal-20.04-amd64-server-*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["099720109477"]
  }

  launch_block_device_mappings {
    device_name = "/dev/sda1"
    volume_size = 50
  }

  ssh_username              = "ubuntu"
  ssh_clear_authorized_keys = "true"

  force_deregister      = "true"
  force_delete_snapshot = "true"

  temporary_iam_instance_profile_policy_document {
    Statement {
      Action   = ["s3:*"]
      Effect   = "Allow"
      Resource = [
        "arn:aws:s3:::gns3-images", "arn:aws:s3:::gns3-images/*"
      ]
    }
    Version = "2012-10-17"
  }
}


build {
  name    = "gns3-server"
  sources = [
    "source.amazon-ebs.ubuntu", "source.vagrant.ubuntu"
  ]
  provisioner "file" {
    only        = [
      "vagrant.ubuntu"
    ]
    source      = "upload"
    destination = "/tmp/"
  }
  provisioner "shell" {
    scripts = [
      "install.sh",
    ]
  }
}

