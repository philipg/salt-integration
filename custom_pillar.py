import common

""" fk has to be the minion_id as thats what salt is looking up.
the only question is, do we want to populate it on vm build, or do we want to populate
the field inside the cmdb on first vm build """

def ext_pillar(minion_id, pillar, *args, **kwargs):
    gerry = common.datagerry()
    data = gerry.get_vm_fuzzy_match(ip='',mac='',hostname=minion_id)

    blob = {}
    for item in data:
        for it in item:
            for itemkey, itemvalue in it.items():
                blob[itemkey] = itemvalue
    pillar = {'cmdb': blob }
    return pillar
ext_pillar()