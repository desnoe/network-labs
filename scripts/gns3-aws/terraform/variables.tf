variable "gns3_instance_type" {
  description = "Instance type of the GNS3 server, e.g. t2.micro or c5.metal"
  type        = string
  default     = "t3.small"
}

variable "my_public_ip_addr" {
  description = "Fixed public IP address to be used to access the GNS3 server"
  type        = string
  default     = "90.127.148.252/32"
}

