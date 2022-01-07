# Packer

These [Packer](https://learn.hashicorp.com/packer) scripts allow setting up fresh GNS3/NetBox images for network labs in
2 flavors:

1) Vagrant images for use on your laptop directly
2) AMI images for use on AWS

## Disclaimer

⚠️ Always read, understand and adapt Packer scripts to your environement!!! ⚠️

## TL;DR

```
packer init .
packer build .
```

## Vagrant images

Make sure you have Virtualbox, Vmware or Parallels installed on your system.

Copy or symlink your QCOW2 images and license files tu the [upload](./upload) folder in 2 folders:

- images
- licenses

If you want to only build the vagrant image:

```
packer build -only=gns3-server.vagrant.ubuntu .
```

## AWS AMI images

Make sure you have AWS credentials somewhere that Packer can rely on (for instance in environment vars).

Copy your QCOW2 images and license files in a S3 bucket, call it s3://gns3-images in 2 folders:

- images
- licenses

If you want to only build the vagrant image:

```
packer build -only=gns3-server.amazon-ebs.ubuntu .
```

If you want to use another S3 bucket name:

```
export PKR_VAR_gns3_images_bucket_name=my_bucket_name
```
