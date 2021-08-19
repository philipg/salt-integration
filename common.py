import requests
import json

USERNAME='admin'
PASSWORD='admin'
    
class datagerry():
    def get_types(self,username, password):
        r = requests.get('http://localhost/rest/types', auth=(username, password))
        return r.json()['results']

    def filter_type_id(self, objtypes, filter_name):
        for objtype in objtypes:
            if objtype.get("name") == filter_name:
                return objtype['public_id']

    def get_objects(self,username, password):
        r = requests.get('http://localhost/rest/objects', auth=(username, password))
        return r.json()['results']

    def filter_object_type_id(self, objtypes, filter_id):
        objects = []
        for objtype in objtypes:
            if objtype.get("type_id") == filter_id:
                objects.append(objtype)
        return objects
    def catagories(self,username, password):
        r = requests.get('http://localhost/rest/catagories', auth=(username, password))
        return r.json['results']

    def get_vm_by_hostname(self, objs, hostname):
        for obj in objs:
            for field in obj['fields']:
                if field.get('name') == 'hostname':
                    if field.get('value') == hostname:
                        return obj
    def get_vm_by_ip(self, objs, ip):
        for obj in objs:
            for field in obj['fields']:
                if field.get('name') == 'ip-address':
                    if field.get('value') == ip:
                        return obj
    def get_vm_by_mac(self, objs, mac):
        for obj in objs:
            for field in obj['fields']:
                if field.get('name') == 'mac-address':
                    if field.get('value') == mac:
                        return obj

    def filter_customer_id(self, objs, cust_id):
        for obj in objs:
            if obj.get('public_id') == cust_id:
                return obj

    def get_vm_field(self, fields, field_name):
        for field in fields:
            if field['name'] == field_name:
                return field['value']

    def field_to_json(self, fields):
        obj = []
        for field in fields:
            arr = {}
            if field.get('name') == 'customer':
                arr['customer_id'] = field.get('value')
            else:
                arr[field.get('name')] = field.get('value')
            obj.append(arr)
        return obj
    
    def get_vm_fuzzy_match(self, ip, mac, hostname):
        types = self.get_types(username='admin', password='admin')
        objects = self.get_objects(username='admin', password='admin')
        vm_type_id = self.filter_type_id(filter_name='virtual-machine', objtypes=types)
        customer_type_id = self.filter_type_id(filter_name='customer', objtypes=types)
        customers = self.filter_object_type_id(objects, filter_id=customer_type_id)
        vms = self.filter_object_type_id(objects, filter_id=vm_type_id)

        vm = None
        ipmatch = self.get_vm_by_ip(vms, ip)
        macmatch = self.get_vm_by_mac(vms, mac)
        hostmatch = self.get_vm_by_hostname(vms, hostname)
        if ipmatch:
            vm = ipmatch
        if macmatch:
            vm = macmatch
        if hostmatch:
            vm = hostmatch

        customer = self.filter_customer_id(customers, self.get_vm_field(vm['fields'], 'customer'))

        vm = self.field_to_json(vm['fields'])
        customer = self.field_to_json(customer['fields'])
    
        return vm, customer
