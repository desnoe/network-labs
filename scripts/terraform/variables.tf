variable "gns3_instance_type" {
  description = "Instance type of the GNS3 server, e.g. t2.micro or c5.metal"
  type        = string
  default     = "t3.small"
}

variable "gns3_images_bucket_name" {
  type = string
  default = "gns3-images"
}
