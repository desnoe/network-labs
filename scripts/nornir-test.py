import click
import os
import logzero
from logzero import logger
from pprint import pprint
from sdwan_automation.nb2gns3 import NetBoxSession, Converter
from nornir import InitNornir
from nornir.core.task import Task, Result
from nornir_utils.plugins.functions import print_result
from nornir.core.filter import F
import time
from expect import Vyos
import pygns3
import urllib.parse

# required for click
os.environ['LANG'] = 'C.UTF-8'


def update_inventory_with_gns3_node(task: Task, gns3_project: pygns3.Project) -> Result:
    node = next(n for n in gns3_project.nodes if n.metadata.name == task.host.name)
    task.host.data['gns3_node'] = node
    return Result(
        host=task.host,
        result=f'Updated GNS3 data inventory for {task.host.name}'
    )


def gns3_node_start(task: Task, sleep: int = 1) -> Result:
    n = task.host.data['gns3_node']

    if n.metadata.status == "started":
        return Result(
            host=task.host,
            result=f'Node {task.host.name} was already started',
            changed=False
        )

    n.start()
    time.sleep(sleep)
    return Result(
        host=task.host,
        result=f'Started node {task.host.name}',
        changed=True
    )


def vyos_configure(task: Task) -> Result:
    n = task.host.data['gns3_node']

    telnet_port = n.metadata.console
    telnet_server = urllib.parse.urlparse(n.server.base_url).hostname

    v = Vyos(host=telnet_server, port=telnet_port)

    v.login("vyos", "vyos")
    v.get_configuration()
    v.logout()
    return Result(
        host=task.host,
        result='\n'.join(v.loglines),
        log='\n'.join(v.loglines)
    )


@click.command()
@click.option('-v', '--verbose', count=True)
@click.option('--netbox-url', envvar='NETBOX_URL', default='http://172.25.41.101:8000', show_default=True,
              help='netbox URL')
@click.option('--netbox-token', envvar='NETBOX_TOKEN', default='0123456789abcdef0123456789abcdef01234567',
              help='netbox API token')
@click.option('--gns3-server-url', envvar='GNS3_SERVER_URL', default='http://172.25.41.101:3080/v2', show_default=True,
              help='GNS3 server URL')
@click.option('--gns3-project-name', envvar='GNS3_PROJECT_NAME', default='lab', show_default=True,
              help='GNS3 project name')
def test(netbox_url, netbox_token, gns3_server_url, gns3_project_name, verbose):

    if verbose == 2:
        logzero.loglevel(logzero.DEBUG)
    elif verbose == 1:
        logzero.loglevel(logzero.INFO)
    else:
        logzero.loglevel(logzero.ERROR)

    nr = InitNornir(
        inventory={
            "plugin": "NetBoxInventory2",
            "options": {
                "nb_url": netbox_url,
                "nb_token": netbox_token
            }
        }
    )

    # GNS3 server
    logger.info(f'Set server {gns3_server_url} ...')
    gns3_server = pygns3.Server(base_url=gns3_server_url)
    gns3_server.projects.pull()
    gns3_project = next(p for p in gns3_server.projects if p.metadata.name == gns3_project_name)
    gns3_project.nodes.pull()

    # update inventory
    result = nr.run(task=update_inventory_with_gns3_node, gns3_project=gns3_project)
    print_result(result)

    # start vyos_routers
    vyos_routers = nr.filter(F(groups__contains="device_role__internet-operator-customer-router"))
    result = vyos_routers.run(task=gns3_node_start, sleep=1)
    print_result(result)

    # configure vyos_routers
    result = vyos_routers.run(task=vyos_configure)
    print_result(result)


if __name__ == '__main__':
    test()
