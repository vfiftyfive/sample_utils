#!/usr/bin/env python
from nested_vsphere.utils import svc_login, create_DVS, add_portgroup_to_VDS, add_host_to_VDS, get_obj
from pyVmomi import vim
import sys


def main():

    si = svc_login(host=sys.argv[1], user=sys.argv[2], port='443', password=sys.argv[3])
    content = si.content

    nsx_dvs = create_DVS(content, 'NSX-HOL', 'my-vds')
    print "VDS {} created".format(nsx_dvs.name)
    portgroup_mo = add_portgroup_to_VDS(content, nsx_dvs, 'Legacy', 345)
    print portgroup_mo.name
    # host_mo = get_obj(content, [vim.HostSystem], '10.48.58.106')
    # add_host_to_VDS(content, host_mo, nsx_dvs, "vmnic2")

if __name__ == '__main__':
    sys.exit(main())
