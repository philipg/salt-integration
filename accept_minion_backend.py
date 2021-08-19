import salt.config
import salt.key
import salt.wheel

master_opts = salt.config.client_config('/etc/salt/master')
skey = salt.key.Key(master_opts)


## verify is a new instance, and appears in our cmdb ##
## could validate based on source ip - that the source ip matches the record/minion_id in the CMDB
## or matches the vsphere unique GUID in the CMDB against the source ip and a secret key? ##

## try:
## and retry
## if cmdb says no; mark record as failed and dont do it

minion_id = 'jenkins'
if minion_id not in skey.list_keys()['minions']:
    wheel = salt.wheel.WheelClient(master_opts)
    wheel.cmd('key.accept', [minion_id])



