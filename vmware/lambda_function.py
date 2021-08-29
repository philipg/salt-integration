import logging
import os
import sys
import json
from typing import Any, Dict
import boto3
import urllib3
import yaml
import vmw_service_instance
import vmw_common
import vmw_cloudinit
import requests
from pyVmomi import vim
from jinja2 import Template

def getresult(si, task):
    while True:
        result = vmw_common.async_task_wait(si, task)
        if result.get('state') != 'running':
            print(result)
            return result
            break

def getspec(specfile):
    spec = open(specfile, 'r')
    return yaml.load(spec)

dynamodb = boto3.resource("dynamodb")

class Action:
    def __init__(self, order_id, spec=getspec('config/vsphere.yml')):
        self.order_id = order_id
        self.spec = spec

    def handle_get_order(self, event: Any) -> Any:
        """Handle get order"""
        table = dynamodb.Table("orders")
        response = table.get_item(
            Key={'order_id': self.order_id}
        )
        blob = {'order_id':event['order_id'], 'order': response['Item']}
        return blob

    def handle_get_ip(self, event: Any) -> Any:
        """Handle get ip"""
        http = urllib3.PoolManager()
        r = http.request('GET', 'http://192.168.100.2/')
        blob = {'order_id':event['order_id'], 'status_code': str(r.data), 'text': r.status}

        return blob

    def handle_get_portgroup(self, event: Any) -> Any:
        """Handle get portgroup"""
        blob = {'order_id':event['order_id']}
        return blob

    def handle_get_cluster(self, event: Any) -> Any:
        """Handle get cluster"""
        blob = {'order_id':event['order_id']}
        return blob

    def handle_get_datastore(self, event: Any) -> Any:
        """Handle get datastore"""
        blob = {'order_id':event['order_id']}
        return blob

    def handle_get_template(self, event: Any) -> Any:
        """Handle get template"""
        blob = {'order_id':event['order_id']}
        return blob

    def handle_get_metadata(self, event: Any) -> Any:
        """Handle get metadata"""
        blob = {'order_id':event['order_id']}
        return blob
    
    def handle_post_cmdb(self, event: Any) -> Any:
        """Handle post cmdb"""
        blob = {'order_id':event['order_id']}
        return blob

    def handle_boot_vm(self, event: Any) -> Any:
        """Handle boot vm"""
        blob = {'order_id':event['order_id']}
        return blob

    def handle_clone_vm(self, event: Any) -> Any:
        """Handle clone vm"""

        vmspec = getspec('config/vmspecs.yml')
        cloudinit = getspec('config/cloudinit.yml')
        si = vmw_service_instance.connect(self.spec)


        userdata_template = Template(cloudinit['cloudinit_userdata'])
        metadata_template = Template(cloudinit['cloudinit_metadata'])

        userdata = userdata_template.render(
            network_ip=vmspec['network']['ip'],
            network_prefix=vmspec['network']['prefix'],
            network_gateway=vmspec['network']['gateway'],
            network_dns=vmspec['network']['dns'],
            domain=vmspec['network']['domain'],
            timezone=vmspec['metadata']['timezone'],
            fqdn=vmspec['metadata']['fqdn'],
            minion_name=vmspec['salt']['minion_name'],
            salt_master=vmspec['salt']['master_name']
        )
        metadata = metadata_template.render(
            admin_username=vmspec['metadata']['admin_username'],
            admin_password=vmspec['metadata']['admin_password'],
            host=vmspec['metadata']['host'],
            fqdn=vmspec['metadata']['fqdn']
        )
        # build cloud-init
        userdata = vmw_cloudinit.encode(userdata)
        metadata = vmw_cloudinit.encode(metadata)

        tasks = []
        if vmspec['backend'] == 'vmware':
            if vmspec['buildtype'] == 'create':
                tasks = [vmw_common.create_vm(si, vmspec, userdata, metadata)]

        if vmspec['buildtype'] == 'clone':
            template = vmw_common.get_template(si, vmspec['template'])
            tasks = [vmw_common.clone_vm(si, vmspec, template, userdata, metadata)]
    
        return {'order_id':event['order_id'], 'task_id': str(tasks[0]), 'vm_id': str(tasks[0].info.entity)}

    def handle_get_minion_key_status(self, event: Any) -> Any:
        vmspec = getspec('config/vmspecs.yml')
        minion_master = vmspec['salt']['master_name']
        minion_id = vmspec['salt']['minion_name']
        
        pre_url = f"http://saltmaster.tuxgrid.com/api/check_pre/{minion_id}/"        
        pre_status = requests.get(pre_url).json()
        return pre_status

    def handle_get_master_key_accept(self, event: Any) -> Any:
        vmspec = getspec('config/vmspecs.yml')
        minion_master = vmspec['salt']['master_name']
        minion_id = vmspec['salt']['minion_name']
        accept_key_url = f"http://saltmaster.tuxgrid.com/api/accept_key/{minion_id}/"

        key_status = self.handle_get_minion_key_status(event)
        if key_status['pre'] == True:
                result = requests.get(accept_key_url).json()
        return result

    def handle_get_clone_status(self, event: Any) -> Any:
        """Handle clone status"""

        task_id = event['CloneTaskResult'].get('task_id')
        vm_id = event['CloneTaskResult'].get('vm_id')

        si = vmw_service_instance.connect(self.spec)

        # hack: get task-761 without the vim.Task:task-761 object. need to get the actual object name instead
        # of converting an object to a name. naaasty
        task = vim.Task(task_id.split(':')[1].strip("'"))
        task._stub = si._stub

        # hack: add it as a list. need to pass/check multiple tasks
        state = vmw_common.async_task_wait(si, [task]).get('state')

        return {'order_id':event['order_id'], 'State': state}

    def handle_set_status_complete_fail(self, event: Any):
        """Handle setting the status complete on failure"""
        #execution_id = event['execution_id']
        return None

    def handle_set_status_complete_success(self, event: Any):
        """Handle setting the status complete on success"""
        #execution_id = event['execution_id']
        return None


def lambda_handler(event: Any, context: Any) -> Any:
    """Handle the lambda event operation"""
    
    operation = event['op']
    order_id = int(event['order_id'])

    action_class = getattr(sys.modules[__name__], 'Action')
    action_instance = action_class(order_id)
    action_instance_method = getattr(action_instance, "handle_" + operation)
    return action_instance_method(event)