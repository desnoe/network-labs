terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  backend "s3" {
    bucket = "network-labs-terraform-states"
    key    = "gns3/lab"
    profile = "dev"
    region = "eu-west-3"
  }

  required_version = ">= 0.14.9"
}

provider "aws" {
  profile = "dev"
  region  = "eu-west-3"
}

resource "aws_default_subnet" "default_az1" {
  availability_zone = "eu-west-3a"
}

resource "aws_security_group" "gns3_sg" {
  name   = "gns3-sg"

  ingress = [
    {
      description      = "SSH"
      from_port        = 22
      to_port          = 22
      protocol         = "tcp"
      cidr_blocks      = [var.my_public_ip_addr]
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      security_groups  = []
      self             = false
    },
    {
      description      = "GNS3 API"
      from_port        = 3080
      to_port          = 3080
      protocol         = "tcp"
      cidr_blocks      = [var.my_public_ip_addr]
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      security_groups  = []
      self             = false
    },
    {
      description      = "NetBox API"
      from_port        = 8080
      to_port          = 8080
      protocol         = "tcp"
      cidr_blocks      = [var.my_public_ip_addr]
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      security_groups  = []
      self             = false
    },
    {
      description      = "GNS3 nodes telnet ports"
      from_port        = 5000
      to_port          = 6000
      protocol         = "tcp"
      cidr_blocks      = [var.my_public_ip_addr]
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      security_groups  = []
      self             = false
    }
  ]

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_network_interface" "gns3_server_eni" {
  security_groups = [aws_security_group.gns3_sg.id]
  subnet_id       = aws_default_subnet.default_az1.id
}

resource "aws_key_pair" "ssh_key" {
  key_name   = "gns3-server-key"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCoBMk3cXJh7kqO4xzD522jIouQskyafFjzIGAs5WaxxJ7ATNhZVw3CBc8b+JAxmk6SoeqpunHBGZLLfb0i4yGoh1Z8LPGBQe17Ao/C8d2c7ieo05jICl/J7VgGYTL5bvFVY3CIRC0eaHX0ivIePl4DDduOAnCWNm0H9FCJP+rEev5WY5qeKE/+uSKpdODI311p52eX0VX2+NnH22UxEEDDD9E9jkQjE7KTzVjM3ym48IyuHOlNG6Ao6TL2uVJ8vUpX2SoOM+ckBNtFmnHYzYoUNGlQatrPemCEsKezbjkaHJR8vkO/WIKQafvGabA+at8IsmoY1zmJbjdawzVHD99P olivier@mbp"
}

data "aws_ami" "gns3_server_ami" {
  most_recent = true
  name_regex  = "^gns3-server-ubuntu-focal-\\d{8}"
  owners      = ["self"]

  filter {
    name   = "name"
    values = ["gns3-server-ubuntu-focal-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "gns3_server" {
  ami                  = data.aws_ami.gns3_server_ami.id
  instance_type        = var.gns3_instance_type
  key_name             = aws_key_pair.ssh_key.key_name
  iam_instance_profile = aws_iam_instance_profile.gns3_server_profile.name

  network_interface {
    network_interface_id = aws_network_interface.gns3_server_eni.id
    device_index         = 0
  }

   root_block_device {
     volume_size = 50
   }

  tags = {
    Name = "GNS3"
  }
}

resource "aws_iam_role" "gns3_server_role" {
  name = "gns3_server_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_instance_profile" "gns3_server_profile" {
  name = "gns3_server_profile"
  role = aws_iam_role.gns3_server_role.name
}

resource "aws_iam_role_policy" "gns3_server_policy" {
  name = "gns3_server_policy"
  role = aws_iam_role.gns3_server_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:*"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:s3:::gns3-images",
          "arn:aws:s3:::gns3-images/*",
          "arn:aws:s3:::delarche-images",
          "arn:aws:s3:::delarche-images/*"
        ]
      },
    ]
  })
}

data "aws_route53_zone" "lab_aws_delarche_fr" {
  name         = "lab.aws.delarche.fr."
  private_zone = false
}

resource "aws_route53_record" "gns3" {
  zone_id = data.aws_route53_zone.lab_aws_delarche_fr.zone_id
  name    = "gns3.${data.aws_route53_zone.lab_aws_delarche_fr.name}"
  type    = "A"
  ttl     = "60"
  records = [aws_instance.gns3_server.public_ip]
}
