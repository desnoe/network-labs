import click
import os
import logzero
import gns3_client
from logzero import logger
import requests_cache
from xml.etree import ElementTree
from pprint import pprint
from urllib.parse import urlparse
from urllib3 import disable_warnings

disable_warnings()


class NetBoxSession(requests_cache.CachedSession):
    def __init__(
        self, base_url=None, netbox_token=None, netbox_private_key=None, *args, **kwargs
    ):
        super(NetBoxSession, self).__init__(*args, **kwargs)  # noqa
        self.headers.update({"Authorization": "Token " + str(netbox_token)})
        self.verify = False
        self.base_url = base_url
        self.cache.clear()
        if netbox_private_key:
            r = self.post(
                "/secrets/get-session-key/", data={"private_key": netbox_private_key}
            )
            j = r.json()
            self.headers.update({"X-Session-Key": j["session_key"]})

    def _get_url(self, url):
        o = urlparse(self.base_url)
        path = o.path + "/" + url
        while "//" in path:
            path = path.replace("//", "/")
        o = o._replace(path=path)  # noqa
        return o.geturl()

    def request(self, method, url, prepend_base_url=True, *args, **kwargs):
        if prepend_base_url:
            url = self._get_url(url)
        logger.debug(f"Request sent: {method} {url}")
        r = super(NetBoxSession, self).request(method, url, *args, **kwargs)
        logger.debug(f"Request status: {r.status_code} {r.reason}")
        return r


class Converter:
    def __init__(
        self, netbox_session: NetBoxSession, gns3_server_url: str, project_name: str
    ) -> None:
        self.nb = netbox_session
        self.gns3_server_url = gns3_server_url
        self.name = project_name
        self.server = None
        self.plan = None

    def compute_target(self, query):
        devices = self.nb.request("GET", query).json()["results"]

        # Server
        logger.info(f"Set server {self.gns3_server_url} ...")
        server = gns3_client.Server(base_url=self.gns3_server_url)
        self.server = server

        # Templates
        pids = set(d["platform"]["id"] for d in devices if d["platform"])
        for pid in pids:
            logger.info(f"Set template for platform id {pid} ...")
            platform = self.nb.request("GET", "/dcim/platforms/" + str(pid)).json()
            params = self.platform_to_template(platform)
            server.templates.append(gns3_client.Template(server=server, **params))

        # Project
        logger.info(f"Set project {self.name} ...")
        project = gns3_client.Project(
            server=server, name=self.name, auto_close=False, auto_open=True
        )
        server.projects.append(project)

        # Drawings
        sids = set(d["site"]["id"] for d in devices if d["site"])
        for sid in sids:
            logger.info(f"Set drawing for site id {sid} ...")
            site = self.nb.request("GET", "/dcim/sites/" + str(sid)).json()
            params = self.site_to_drawing(site)
            project.drawings.append(gns3_client.Drawing(project=project, **params))

        # Nodes
        for device in devices:
            logger.info(f'Set node for device {device["name"]} ...')
            device["interfaces"] = self.nb.get(
                "/dcim/interfaces/?q=&device_id=" + str(device["id"])
            ).json()["results"]
            device["platform"] = self.nb.request(
                "GET", "/dcim/platforms/" + str(device["platform"]["id"])
            ).json()
            sid = device["site"]["id"]
            site = self.nb.request("GET", "/dcim/sites/" + str(sid)).json()
            params = self.device_to_node(device, site)
            template_name = params.pop("template")
            template = next(
                t for t in server.templates if t.metadata.name == template_name
            )
            project.nodes.append(
                gns3_client.Node(project=project, template=template, **params)
            )

        # Links
        logger.info(f"Set links ...")

        dids = set(d["id"] for d in devices)
        connections = set()
        for device in devices:
            c = [
                (i["id"], i["connected_endpoint"]["id"])
                for i in device["interfaces"]
                if i["connected_endpoint_type"] == "dcim.interface"
                and i["connected_endpoint"]["device"]["id"] in dids
                and i["connected_endpoint"]["device"]["id"] >= i["device"]["id"]
            ]
            connections.update(c)

        for c in connections:
            params = self.connection_to_link(
                c[0], c[1], devices=devices, project=project
            )
            project.links.append(gns3_client.Link(project=project, **params))

    def compute_plan(self):
        logger.info(f"Computing plan based on diff ...")
        templates_plan = self.server.templates.diff()
        templates_plan["delete"] = [
            t
            for t in templates_plan["delete"]
            if t.metadata.name
            not in ["Cloud", "VPCS", "Ethernet switch", "Ethernet hub"]
        ]

        projects_plan = self.server.projects.diff()
        project = next(p for p in self.server.projects if p.metadata.name == self.name)

        drawings_plan, nodes_plan, links_plan = (
            project.drawings.diff(),
            project.nodes.diff(),
            project.links.diff(),
        )

        self.plan = {
            "delete": templates_plan["delete"]
            + projects_plan["delete"]
            + drawings_plan["delete"]
            + nodes_plan["delete"]
            + links_plan["delete"],
            "create": templates_plan["create"]
            + projects_plan["create"]
            + drawings_plan["create"]
            + nodes_plan["create"]
            + links_plan["create"],
            "update": templates_plan["update"]
            + projects_plan["update"]
            + drawings_plan["update"]
            + nodes_plan["update"]
            + links_plan["update"],
        }

    def apply_plan(self):
        logger.info(f"Applying plan ...")
        for obj in self.plan["delete"]:
            obj.delete()
        for obj in self.plan["create"]:
            obj.create()
        for obj in self.plan["update"]:
            obj.update()

    @staticmethod
    def platform_to_template(platform):
        params = {"name": platform["name"]}

        for k in vars(gns3_client.TemplateMetadata()).keys():
            cf = "gns3_" + k
            if cf in platform["custom_fields"]:
                params[k] = platform["custom_fields"][cf]

        return params

    @staticmethod
    def site_to_drawing(site):
        params = {"name": site["name"]}

        for k in vars(gns3_client.DrawingMetadata()).keys():
            cf = "gns3_" + k
            if cf in site["custom_fields"]:
                params[k] = site["custom_fields"][cf]

        height = site["custom_fields"]["gns3_height"]
        width = site["custom_fields"]["gns3_width"]
        svg = (
            f'<svg height="{height}" width="{width}">'
            f'<rect fill="#b0b0b0" fill-opacity="1.0" height="{height}" width="{width}" />'
            f"</svg>"
        )
        xml = ElementTree.fromstring(svg)
        params["svg"] = ElementTree.tostring(xml, encoding="unicode")

        return params

    @staticmethod
    def device_to_node(device, site):
        params = {"name": device["name"], "template": device["platform"]["name"]}

        custom_adapters = Converter.device_custom_adapters(device)
        if custom_adapters:
            params["custom_adapters"] = custom_adapters

        properties = Converter.device_properties(device)
        if properties:
            params["properties"] = properties

        for k in vars(gns3_client.NodeMetadata()).keys():
            cf = "gns3_" + k
            if cf in device["custom_fields"]:
                params[k] = device["custom_fields"][cf]

        for cf in ("x", "y", "z"):
            params[cf] += site["custom_fields"]["gns3_" + cf]

        return params

    @staticmethod
    def device_get_physical_interfaces(device):
        return [
            i for i in device["interfaces"] if i["type"]["value"] not in ["virtual"]
        ]

    @staticmethod
    def device_custom_adapters(device):
        template_type = device["platform"]["custom_fields"]["gns3_template_type"]
        if template_type in ["qemu", "docker"]:
            custom_adapters = list()
            for n, i in enumerate(Converter.device_get_physical_interfaces(device)):
                custom_adapter = {"port_name": i["name"], "adapter_number": n}
                custom_adapters.append(custom_adapter)
            return custom_adapters

    @staticmethod
    def device_properties(device):
        template_type = device["platform"]["custom_fields"]["gns3_template_type"]
        if template_type in ["qemu", "docker"]:
            return {"adapters": len(Converter.device_get_physical_interfaces(device))}
        if template_type == "ethernet_switch":
            ports_mapping = list()
            for n, i in enumerate(Converter.device_get_physical_interfaces(device)):
                mode: str = "access"
                nb_mode: dict = i["mode"]
                if isinstance(nb_mode, dict) and "value" in nb_mode:
                    if nb_mode["value"] == "tagged-all":
                        mode = "dot1q"

                vlan: int = 1
                nb_vlan: dict = i["untagged_vlan"]
                if isinstance(nb_vlan, dict) and "vid" in nb_vlan:
                    vlan = nb_vlan["vid"]

                port_mapping = {
                    "ethertype": "",
                    "name": i["name"],
                    "port_number": n,
                    "type": mode,
                    "vlan": vlan,
                }
                ports_mapping.append(port_mapping)
            return {"ports_mapping": ports_mapping}

    @staticmethod
    def connection_to_link(
        interface_id_a: dict,
        interface_id_b: dict,
        devices: dict,
        project: gns3_client.Project,
    ) -> dict:
        int_a = next(
            i for d in devices for i in d["interfaces"] if i["id"] == interface_id_a
        )
        int_b = next(
            i for d in devices for i in d["interfaces"] if i["id"] == interface_id_b
        )

        node_a = next(
            n for n in project.nodes if n.metadata.name == int_a["device"]["name"]
        )
        node_b = next(
            n for n in project.nodes if n.metadata.name == int_b["device"]["name"]
        )

        interface_id_to_num = {
            d["id"]: {
                i["id"]: n
                for n, i in enumerate(Converter.device_get_physical_interfaces(d))
            }
            for d in devices
        }

        number_a = interface_id_to_num[int_a["device"]["id"]][int_a["id"]]
        number_b = interface_id_to_num[int_b["device"]["id"]][int_b["id"]]

        port_number_a, adapter_number_a = number_a, 0
        if node_a.template.metadata.template_type in ["qemu", "docker"]:
            port_number_a, adapter_number_a = 0, number_a

        port_number_b, adapter_number_b = number_b, 0
        if node_b.template.metadata.template_type in ["qemu", "docker"]:
            port_number_b, adapter_number_b = 0, number_b

        params = {
            "nodes": [
                {
                    "node": node_a,
                    "port_number": port_number_a,
                    "adapter_number": adapter_number_a,
                },
                {
                    "node": node_b,
                    "port_number": port_number_b,
                    "adapter_number": adapter_number_b,
                },
            ]
        }

        return params


# required for click
os.environ["LANG"] = "C.UTF-8"


@click.command()
@click.option("-v", "--verbose", count=True)
@click.option(
    "--sync/--no-sync",
    default=True,
    show_default=True,
    help="sync mode (push to GNS3 if needed) or dry-run mode (read-only)",
)
@click.option(
    "--netbox-url",
    envvar="NETBOX_URL",
    default="http://netbox.example.com:8000/api",
    show_default=True,
    help="netbox URL",
)
@click.option(
    "--netbox-token",
    envvar="NETBOX_TOKEN",
    default="0123456789abcdef0123456789abcdef01234567",
    help="netbox API token",
)
@click.option(
    "--gns3-server-url",
    envvar="GNS3_SERVER_URL",
    default="http://gns3.example.com:3080/v2",
    show_default=True,
    help="GNS3 server URL",
)
@click.option(
    "--gns3-project-name",
    envvar="GNS3_PROJECT_NAME",
    default="lab",
    show_default=True,
    help="GNS3 project name",
)
def nb2gns3(
    sync, netbox_url, netbox_token, gns3_server_url, gns3_project_name, verbose
):
    if verbose == 2:
        logzero.loglevel(logzero.DEBUG)
    elif verbose == 1:
        logzero.loglevel(logzero.INFO)
    else:
        logzero.loglevel(logzero.ERROR)

    if not sync:
        logger(
            f"DRY-RUN mode, nothing will be commited to GNS3. Use --sync to commit to netbox."
        )

    netbox_session = NetBoxSession(netbox_url, netbox_token)
    c = Converter(netbox_session, gns3_server_url, gns3_project_name)
    c.compute_target(query="/dcim/devices/?limit=0&q=&tag=gns3")
    c.compute_plan()

    logger.info(f"This is the plan:")
    logger.info(pprint(c.plan))

    if sync and len(c.plan) > 0:
        c.apply_plan()


if __name__ == "__main__":
    nb2gns3()
