import yaml
import vmw_service_instance
import vmw_common
import vmw_cloudinit

def getresult(si, task):
    while True:
        result = vmw_common.async_task_wait(si, task)
        if result.get('state') != 'running':
            print(result)
            break

def getspec(specfile):
    spec = open(specfile, 'r')
    return yaml.load(spec)

def build(specification, si):
    spec = getspec(specification)

    # build cloud-init
    userdata = vmw_cloudinit.encode(spec['cloudinit_userdata'])
    metadata = vmw_cloudinit.encode(spec['cloudinit_metadata'])

    if spec['backend'] == 'vmware':
        if spec['buildtype'] == 'create':
            create_task = [vmw_common.create_vm(si, spec, userdata, metadata)]
            result = getresult(si, create_task)

        if spec['buildtype'] == 'clone':
            template = vmw_common.get_template(si, spec['template'])
            clone_task = [vmw_common.clone_vm(si, spec, template, userdata, metadata)]
            result = getresult(si, clone_task)


    # customise_task = [vmw_common.customise_vm(si, spec)]
    # vm = vmw_common.power_on(si, spec)
    # print(vmw_common.print_short_detail_list(vm))

    # VM's extra configuration dictionary

    #   -e guestinfo.metadata="${METADATA}" \
    #   -e guestinfo.metadata.encoding="gzip+base64" \
    #   -e guestinfo.userdata="${USERDATA}" \
    #   -e guestinfo.userdata.encoding="gzip+base64"


if __name__ == '__main__':
    args = getspec('config/vsphere.yml')
    si = vmw_service_instance.connect(args)
    build('config/vmspecs.yml', si)