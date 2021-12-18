#!/bin/bash
set -ex

echo "waiting 180 seconds for cloud-init to update /etc/apt/sources.list"
timeout 180 /bin/bash -c \
  'until stat /var/lib/cloud/instance/boot-finished 2>/dev/null; do echo waiting ...; sleep 1; done'

# Update hostname
sudo hostnamectl set-hostname gns3

# Update system
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y curl unzip git

# Installing GNS3
curl -o /tmp/gns3-remote-install.sh https://raw.githubusercontent.com/GNS3/gns3-server/master/scripts/remote-install.sh
sudo bash /tmp/gns3-remote-install.sh
rm /tmp/gns3-remote-install.sh

# Create management bridge for GNS3 labs
sudo tee /etc/netplan/10-gns3-custom.yaml <<EOF
network:
    version: 2
    renderer: networkd
    bridges:
        br-mgmt:
            addresses: [ 192.168.123.0/24 ]
EOF

# Install docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version

# Install NetBox
git clone -b 1.5.1 https://github.com/netbox-community/netbox-docker.git
cd netbox-docker
tee docker-compose.override.yml <<EOF
version: '3.4'
services:
  netbox:
    ports:
      - 8080:8080
  postgres:
    ports:
      - 5432:5432
EOF
sudo tee /etc/systemd/system/netbox.service <<EOF
[Unit]
Description=Netbox
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/netbox-docker
ExecStartPre=/usr/local/bin/docker-compose down
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo docker-compose pull
sudo systemctl start netbox.service
sudo systemctl status netbox.service
sudo systemctl enable netbox.service

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
aws --version
rm -rf aws
rm awscliv2.zip
set -ex

# Copy images
sudo aws s3 sync s3://gns3-images/images/ /opt/gns3/images/QEMU
sudo chown gns3: /opt/gns3/images/QEMU/*

# Install TFTP server and licenses
sudo apt-get install -y tftpd-hpa
sudo aws s3 sync s3://gns3-images/licenses/ /srv/tftp/
sudo chown -R tftp:tftp /srv/tftp/
