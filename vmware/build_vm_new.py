from pyVmomi import vim
import vmw_common


this_vm['creation_date'] = str(datetime.datetime.now())
this_vm['expiry_date'] = str(datetime.datetime.now() + datetime.timedelta(+1))
this_vm['stage'] = 'bootstrap'
this_vm['stage_lastchange'] = str(datetime.datetime.now())
this_vm['networks'] = networks
this_vm['networkdata'] = networkdata
this_vm['cloud-init'] = {}
this_vm['cloud-init']['ssh_authorized_keys'] = []
this_vm['cloud-init']['ssh_authorized_keys'].append(request.form['ssh_authorized_keys'])
this_vm['cloud-init']['hostname'] = hostname
this_vm['cloud-init']['fqdn'] = '%s.lab.darktech.org.uk' % hostname
this_vm['cloud-init']['manage_etc_hosts'] = True
this_vm['cloud-init']['manage_resolv_conf'] = True
this_vm['cloud-init']['packages'] = ['open-vm-tools', 'salt-minion']
this_vm['cloud-init']['resolv_conf'] = {}
this_vm['cloud-init']['resolv_conf']['nameservers'] = ['8.8.8.8', '8.8.4.4']
this_vm['cloud-init']['bootcmd'] = ['systemctl enable vmtoolsd && systemctl enable salt-minion']
this_vm['cloud-init']['power_state'] = {}
this_vm['cloud-init']['power_state']['mode'] = 'reboot'
this_vm['cloud-init']['phone_home'] = {}
this_vm['cloud-init']['phone_home']['url'] = 'http://149.255.99.178/build/staging/%s' % (uuid)
this_vm['cloud-init']['phone_home']['post'] = [ 'instance_id' ]
this_vm['cloud-init']['salt_minion'] = {}
this_vm['cloud-init']['salt_minion']['conf'] = {}
this_vm['cloud-init']['salt_minion']['conf']['master'] = "puppet.lab.darktech.org.uk"
this_vm['cloud-init']['yum_repos'] = {}
this_vm['cloud-init']['yum_repos']['salt-latest'] = {}
this_vm['cloud-init']['yum_repos']['salt-latest']['baseurl'] = 'https://repo.saltstack.com/yum/redhat/7/$basearch/latest'
this_vm['cloud-init']['yum_repos']['salt-latest']['enabled'] = True
this_vm['cloud-init']['yum_repos']['salt-latest']['failovermethod'] = 'priority'
this_vm['cloud-init']['yum_repos']['salt-latest']['gpgcheck'] = False
this_vm['cloud-init']['yum_repos']['salt-latest']['name'] = 'SaltStack Latest Release Channel for RHEL/CentOS $releasever'
this_vm['cloud-init']['package_upgrade'] = True

this_vm['cloud-image'] = request.form['cloud-image']
vm_list.append(this_vm)

def build(specs):
    moref = vmw_common.provision_vm(si, specs)
    uuid = moref.summary.config.uuid

    networks = []
	vm_hardware = moref.config.hardware
	for each_vm_hardware in vm_hardware.device:
		if (each_vm_hardware.key >= 4000) and (each_vm_hardware.key < 5000):
			a_network = {}
			a_network['label'] = each_vm_hardware.deviceInfo.label
			a_network['summary'] = each_vm_hardware.deviceInfo.summary
			a_network['macaddress'] = each_vm_hardware.macAddress
			networks.append(a_network)
    
def get_iso(uuid):
	out = if_exists(uuid)
	if out:
		drive = test.cloudinit.configdrive(node_uuid=uuid)
		drive.set_user_data(userdata=out['cloud-init'])
		###################################
		### nasty hack to add network data
		### please get rid of this and do it properly
		##################################
		drive.set_network_data(out['networkdata'])
		create = drive.create(repository='localhost')
		iso = drive.gen_iso(content=create,node_uuid=uuid,drv=create)
		if iso:
			try:
				### upload iso to datastore for vmware to pick up
				uploader = test.datastoreupload.uploader()
				uploader.upload_iso('/isos/cloudinit-%s.iso' % (uuid),iso)

				return send_file(iso, as_attachment=True)
			except Exception as e:
				print e
				return abort(404)
		else:
			return abort(404)
	else:
		return abort(404)


import logging, subprocess, tempfile, os, StringIO, json, yaml

class configdrive(object):
	def __init__(self, node_uuid, file_ext='.cfgd'):
		self.node_uuid = node_uuid
		self.configdrive_ext = file_ext
		self.meta_data = {'uuid': self.node_uuid}
		self.user_data = {}
		self.configdrive_id = self.node_uuid + self.configdrive_ext
		self.logger = logging.getLogger(self.__class__.__name__)

	def set_meta_data(self, public_keys=[]):
		self.meta_data['public-keys'] = {}
		if public_keys:
			counter = 0
			for key in public_keys:
				index = str(counter)
				self.meta_data['public-keys'][index] = {'openssh-key': key}
				counter += 1
			else:
				self.meta_data['public-keys']['0'] = {'openssh-key': ''}

	def set_user_data(self, nameservers=[], networks={}, userdata={}):
			self.user_data = userdata

#		if nameservers:
#			self.user_data['dns'] = {'nameserver': nameservers}
#		if networks:
#			self.user_data['networks'] = networks
#		else:
#			self.user_data['networks'] = {}
#			self.user_data['networks']['default'] = {
#						'type': 'dynamic',
#						'use_dhcp': True
#			}
	def set_network_data(self, networkdata={}):
			self.network_data = networkdata

	def create(self, repository, create_files=True):
		try:
			temp_dir = tempfile.mkdtemp('_configdrive')
			temp_dir_ec2 = os.path.join(temp_dir, 'ec2', 'latest')
			temp_dir_openstack = os.path.join(temp_dir, 'openstack', 'latest')
			os.makedirs(temp_dir_ec2)
			os.makedirs(temp_dir_openstack)
			cfgdrive_user_yaml = yaml.dump(
				self.user_data, default_flow_style=False, allow_unicode = True,
			)

			cfgdrive_meta_json = json.dumps(
				self.meta_data, indent=4, separators=(',',': ')
			)
                        cfgdrive_network_json = json.dumps(
                                self.network_data, indent=4, separators=(',',': ')
                        )

			user_data_tmp_file = os.path.join(temp_dir_openstack, 'user_data')
			meta_data_tmp_file = os.path.join(temp_dir_openstack, 'meta_data.json')
			network_data_tmp_file = os.path.join(temp_dir_openstack, 'network_data.json')

			with open(user_data_tmp_file, 'w') as outfile:
				outfile.write('#cloud-config\n')
				outfile.write(cfgdrive_user_yaml)
				outfile.close()
			with open(meta_data_tmp_file, 'w') as outfile:
				outfile.write(cfgdrive_meta_json)
				outfile.close()
			with open(network_data_tmp_file, 'w') as outfile:
				outfile.write(cfgdrive_network_json)
				outfile.close()
			return temp_dir

		except Exception as e:
			print e

	def gen_iso(self, content, node_uuid,drv):
		try:
			iso_path = '%s.iso' % node_uuid
			subprocess.call(['mkisofs', '-R', '-V', 'config-2', '-o', iso_path, drv])
		except Exception as e:
			print e

		return iso_path

if __name__ == '__main__':
	drive = configdrive(node_uuid='the-uuid')
	drive.set_user_data()
	drv = drive.create(repository='localhost')
	drive.gen_iso(content=drv,node_uuid='the-uuid',drv=drv)
    