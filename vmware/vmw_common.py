from pyVmomi import vim, vmodl


def async_task_wait(service_instance, tasks):
    for task in tasks:
        if task.info.state == vim.TaskInfo.State.running:
            return {'state': 'running', 'result': task.info}
        if task.info.state == vim.TaskInfo.State.success:
            if task.info.result is not None:
                return {'state': 'success', 'result': task.info.result}
            else:
                return {'state': 'success', 'result': None}
        else:
            return {'state': 'failure', 'result': task.info.error}

def wait_for_tasks(service_instance, tasks):
    """Given the service instance si and tasks, it returns after all the
   tasks are complete
   """
    property_collector = service_instance.content.propertyCollector
    task_list = [str(task) for task in tasks]
    # Create filter
    obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                 for task in tasks]
    property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                               pathSet=[],
                                                               all=True)
    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = obj_specs
    filter_spec.propSet = [property_spec]
    pcfilter = property_collector.CreateFilter(filter_spec, True)
    try:
        version, state = None, None
        # Loop looking for updates till the state moves to a completed state.
        while len(task_list):
            update = property_collector.WaitForUpdates(version)
            for filter_set in update.filterSet:
                for obj_set in filter_set.objectSet:
                    task = obj_set.obj
                    for change in obj_set.changeSet:
                        if change.name == 'info':
                            state = change.val.state
                        elif change.name == 'info.state':
                            state = change.val
                        else:
                            continue

                        if not str(task) in task_list:
                            continue

                        if state == vim.TaskInfo.State.success:
                            # Remove task from taskList
                            task_list.remove(str(task))
                        elif state == vim.TaskInfo.State.error:
                            raise task.info.error
            # Move to next version
            version = update.version
    finally:
        if pcfilter:
            pcfilter.Destroy()

def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)

    for view in container.view:
        if view.name == name:
            obj = view
            break
    return obj


def create_cdrom(vm, si, ISO, op):
    spec = vim.vm.device.VirtualDeviceSpec()
    if op == 'add':
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    elif op == 'edit':
        spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit

    spec.device = vim.vm.device.VirtualCdrom()
    spec.device.key = 3000
    spec.device.controllerKey = 200
    spec.device.unitNumber = 0

    spec.device.deviceInfo = vim.Description()
    spec.device.deviceInfo.label = 'CD/DVD drive 1'
    spec.device.deviceInfo.summary = 'ISO'

    spec.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
    spec.device.backing.fileName = ISO

    spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    spec.device.connectable.startConnected = True
    spec.device.connectable.allowGuestControl = True
    spec.device.connectable.connected = False
    spec.device.connectable.status = 'untried'


    configspec = vim.vm.ConfigSpec()
    configspec.deviceChange = [spec]
    dev_changes = []
    dev_changes.append(spec)
    configspec.deviceChange = dev_changes

    print("creating cdrom")
    task = []
    task.append(vm.ReconfigVM_Task(spec=configspec))
    wait_for_tasks(si, task)

def add_scsi_controller(vm, si):
    spec = vim.vm.ConfigSpec()
    dev_changes = []
    controller_spec = vim.vm.device.VirtualDeviceSpec()
    controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    controller_spec.device = vim.vm.device.VirtualLsiLogicController()
    controller_spec.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
    dev_changes.append(controller_spec)
    spec.deviceChange = dev_changes
    task = []
    task.append(vm.ReconfigVM_Task(spec=spec))
    wait_for_tasks(si, task)
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualSCSIController):
            return dev


def add_disk(vm, si, disk_size):
    spec = vim.vm.ConfigSpec()
    unit_number = 0
    controller = None
    # get all disks on a VM, set unit_number to the next available
    for dev in vm.config.hardware.device:
        if hasattr(dev.backing, 'fileName'):
            unit_number = int(dev.unitNumber) + 1
            # unit_number 7 reserved for scsi controller
            if unit_number == 7:
                unit_number += 1
            if unit_number >= 16:
                print("we don't support this many disks")
                return
        if isinstance(dev, vim.vm.device.VirtualSCSIController):
            controller = dev
            print("We have a controller")
    # add disk here
    dev_changes = []
    new_disk_kb = int(disk_size) * 1024 * 1024
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    disk_spec.device.backing.thinProvisioned = True
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.capacityInKB = new_disk_kb
    if controller is None:
        print("creating new controller")
        controller = add_scsi_controller(vm, si)
    disk_spec.device.controllerKey = controller.key
    dev_changes.append(disk_spec)
    spec.deviceChange = dev_changes
    vm.ReconfigVM_Task(spec=spec)


def add_network(vm, si, content, netName):
    spec = vim.vm.ConfigSpec()
    dev_changes = []
    network_spec = vim.vm.device.VirtualDeviceSpec()
    network_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    network_spec.device = vim.vm.device.VirtualVmxnet3()
    print("Getting a network...")
    # Get network type
    for net in content.rootFolder.childEntity[0].network:
        if net.name == netName:
            if isinstance(net, vim.dvs.DistributedVirtualPortgroup):
                # Run portgroup code
                pg_obj = get_obj(
                    content, [vim.dvs.DistributedVirtualPortgroup], netName)
                dvs_port_connection = vim.dvs.PortConnection()
                dvs_port_connection.portgroupKey = pg_obj.key
                dvs_port_connection.switchUuid = pg_obj.config.distributedVirtualSwitch.uuid
                network_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                network_spec.device.backing.port = dvs_port_connection
                break
            elif isinstance(net, vim.Network):
                # Run plain network code
                network_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                network_spec.device.backing.network = get_obj(
                    content, [vim.Network], netName)
                network_spec.device.backing.deviceName = netName
                break
        else:
            print("This name is not a network")

    # Allow the network card to be hot swappable
    network_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    network_spec.device.connectable.startConnected = True
    network_spec.device.connectable.allowGuestControl = True

    dev_changes.append(network_spec)
    spec.deviceChange = dev_changes
    task = []
    task.append(vm.ReconfigVM_Task(spec=spec))
    wait_for_tasks(si, task)

def get_template(si, template_name):
    content = si.content
    template = get_obj(content, [vim.VirtualMachine], template_name)
    return template

def clone_vm(si, specs, template, userdata=None, metadata=None):
    content = si.content
    vm_name = specs['name']
    datastore = specs['datastore']
    datastore_path = f'[{datastore}] {vm_name}'
    datacenters = content.rootFolder.childEntity

    datacenter = None
    for dc in datacenters:
        if dc.name == specs['datacenter']:
            datacenter = dc
    
    for folder in datacenter.vmFolder.childEntity:
        if folder.name == specs['vm_folder']:
            vm_folder = folder
            break

    resource_pool = get_obj(si.content, [vim.ResourcePool], specs['resourcepool'])
    datastore = get_obj(si.content, [vim.Datastore], datastore)

    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool

    vmx_file = vim.vm.FileInfo(
        logDirectory=None,
        snapshotDirectory=None,
        suspendDirectory=None,
        vmPathName=datastore_path
    )

    config = vim.vm.ConfigSpec(
        name=vm_name,
        memoryMB=int(specs['mem']),
        numCPUs=int(specs['cpus']),
        files=vmx_file,
        guestId=specs['guestid'],
        version=str(specs['vm_version'])
    )

    options_values = {}
    if 'user' in specs:
        options_values.update({"User": specs['user']})
    if 'application' in specs:
        options_values.update({"Application": specs['application']})
    if metadata:
        options_values.update({"guestinfo.metadata": metadata})
        options_values.update({"guestinfo.metadata.encoding": 'gzip+base64'})
        
    if userdata:
        options_values.update({"guestinfo.userdata": userdata})
        options_values.update({"guestinfo.userdata.encoding": 'gzip+base64'})

    for optionkey, optionvalue in options_values.items():
        opt = vim.option.OptionValue()
        opt.key = optionkey
        opt.value = optionvalue
        config.extraConfig.append(opt)        

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.powerOn = True
    clonespec.config = config

    return template.Clone(folder=vm_folder, name=vm_name, spec=clonespec)


def create_vm(si, specs, userdata=None, metadata=None):
    content = si.content
    vm_name = specs['name']
    datastore = specs['datastore']
    datastore_path = f'[{datastore}] {vm_name}'
    datacenters = content.rootFolder.childEntity

    datacenter = None
    for dc in datacenters:
        if dc.name == specs['datacenter']:
            datacenter = dc
    
    for folder in datacenter.vmFolder.childEntity:
        if folder.name == specs['vm_folder']:
            vm_folder = folder
            break

    resource_pool = get_obj(si.content, [vim.ResourcePool], specs['resourcepool'])


    vmx_file = vim.vm.FileInfo(logDirectory=None, snapshotDirectory=None, suspendDirectory=None, vmPathName=datastore_path)
    config = vim.vm.ConfigSpec(name=vm_name, memoryMB=int(specs['mem']), numCPUs=int(specs['cpus']), files=vmx_file, guestId=specs['guestid'], version=str(specs['vm_version']))

    config.extraConfig = []
    opt = vim.option.OptionValue()
    options_values = {}
    if 'user' in specs:
       options_values.update({"User": specs['user']})
    if 'application' in specs:
       options_values.update({"Application": specs['application']})

    for optionkey, optionvalue in options_values.items():
        opt = vim.option.OptionValue()
        opt.key = optionkey
        opt.value = optionvalue
        config.extraConfig.append(opt)

    return vm_folder.CreateVM_Task(config=config, pool=resource_pool)

def get_vm_by_path(si, datastore_name, datacenter_name, vm_name):
    content = si.content
    datacenters = content.rootFolder.childEntity
    datastore_path = f"[{datastore_name}] {vm_name}/{vm_name}.vmx"

    for dc in datacenters:
        if dc.name == datacenter_name:
            datacenter = dc
    return content.searchIndex.FindByDatastorePath(datacenter, datastore_path)

def customise_vm(si, specs):
    content = si.content
    vm = get_vm_by_path(si, specs['datastore'], specs['datacenter'], specs['name'])

    if vm is not None:
        for disk in specs['disks']:
            # we should check if the disk exists first based on its name/location
            add_disk(vm=vm, si=si, disk_size=disk['size'])
            
        for network in specs['networks']:
            add_network(vm, si, content, network['name'])


    if specs['iso']:
        create_cdrom(vm=vm, si=si, ISO=specs['iso'], op='add')

def print_short_detail_list(vm):
    vm_summary = vm.summary
    a = vm_summary
    del vars(a.config)['product']
    del vars(a.runtime)['device']
    del vars(a.runtime)['offlineFeatureRequirement']
    del vars(a.runtime)['featureRequirement']
    fullData = vars(a.config)
    del vars(a.guest)['guestId']
    fullData.update(guest=vars(a.guest))
    fullData.update(storage=vars(a.storage))
    fullData.update({"overallStatus": a.overallStatus})
    fullData.update({"powerState": a.runtime.powerState})
    fullData.update({"bootTime": a.runtime.bootTime})

    # Grab the tags from vm.config
    tags = {}
    for opts in vm.config.extraConfig:
        if opts.key == "Language":
            tags.update({opts.key: opts.value})
        elif opts.key == "User":
            tags.update({opts.key: opts.value})
        elif opts.key == "Application":
            tags.update({opts.key: opts.value})
    fullData.update({"extraConfig": tags})

    b = vars(a.runtime.host.summary.config.product)
    del vars(a.runtime.host.summary.config)['product']
    hostDetails = vars(a.runtime.host.summary.config)
    hostDetails.update(product=b)
    del hostDetails['featureVersion']
    fullData.update(host=hostDetails)
    return fullData

def power_on(si, specs):
    content = si.content
    vm = get_vm_by_path(si, specs['datastore'], specs['datacenter'], specs['name'])
    vm.PowerOnVM_Task()
    return vm

