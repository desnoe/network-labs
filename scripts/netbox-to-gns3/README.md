# Netbox to GNS3

This script translates data in Netbox to HTTP calls on the GNS3 server REST API.

## TL;DR

```
python3 nb2gns3.py --help
Usage: nb2gns3.py [OPTIONS]

Options:
  -v, --verbose
  --sync / --no-sync        sync mode (push to GNS3 if needed) or dry-run mode
                            (read-only)  [default: sync]
  --netbox-url TEXT         netbox URL  [default:
                            http://netbox.example.com:8000/api]
  --netbox-token TEXT       netbox API token
  --gns3-server-url TEXT    GNS3 server URL  [default:
                            http://gns3.example.com:3080/v2]
  --gns3-project-name TEXT  GNS3 project name  [default: lab]
  --help                    Show this message and exit.
```

## Examples

```
python3 nb2gns3.py -v \
--gns3-server-url http://gns3.lab.aws.delarche.fr:3080/v2 \
--netbox-url http://gns3.lab.aws.delarche.fr:8080/api
```
