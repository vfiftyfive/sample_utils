#!/usr/bin/env python
import nested_vsphere.utils as utils
import nested_vsphere.vesx as vesx
import sys
import os


# user = 'cpaggen'
# password = 'ins3965!'
# name_list = ['student-01-vesx-01', 'student-01-vesx-02', 'student-01-vesx-03']
# host = '10.48.58.109'
# port = '443'
# compute_host = '10.48.58.110'
# datastore = 'Nimble-Lun-11'
# vmfolder = 'vesxi'
# mgmt_network = 'Backbone'
# network = 'nested-VTEP'
# iso = '[Nimble-Lun-11] Sources/VMware-VMvisor-Installer-6.0.0.update03-5050593.x86_64.iso'
# mem = 16384
# vcpu = 4
# guestid = 'vmkernel5Guest'
# vmx_version = 'vmx-10'
# disk_size = 40

trailer = ">>>>>>>  "

def distribute_resources(consumer, resource):

    j = 0
    res = [[] for _ in range(resource)]

    while j < len(consumer):
        for i in range(resource):
            if j == len(consumer):
                break
            res[i].append(consumer[j])
            j += 1
    return res


def main():

    si = utils.svc_login(host=os.environ['HOST'], user=os.environ['USER'], port='443', password=os.environ['PASSWORD'])

    name_list = os.environ['VMNAME_LIST'].split(',')
    compute_host_list = os.environ['COMPUTE_HOSTS'].split(',')
    vm_distribution = distribute_resources(name_list, len(compute_host_list))

    host_index = 0
    for host in vm_distribution:
        dest_host = compute_host_list[host_index]
        host_index += 1
        for vm in host:
            try:
                nested_vm = vesx.VESX(vm_name=vm, host=dest_host,
                                      datastore=os.environ['DATASTORE'], vmfolder=os.environ['VMFOLDER'],
                                      network=os.environ['NETWORK'], mgmt_network=os.environ['MGMT_NETWORK'],
                                      iso=os.environ['ISO'], mem=int(os.environ['MEM']), vcpu=int(os.environ['VCPU']),
                                      si=si, guestid=os.environ['GUESTID'], vmx_version=os.environ['VMX_VERSION'],
                                      disk_size=int(os.environ['DISK_SIZE']))
                print "\n\n{}Deploying VM {} on host {}".format(trailer, vm, dest_host)
                res = nested_vm.deploy_vm_task()
                if res.info.state == 'error':
                    raise ValueError(res.info.error.msg)
                res = nested_vm.boot()
                if res.info.state == 'error':
                    raise ValueError(res.info.error.msg)

                print "{}Connecting VNC console: {}::{}\n".format(trailer, dest_host, nested_vm.vnc_port)
                for i in range(10):
                    os.system("vncdo -s {}::{} key tab pause 1".format(dest_host, nested_vm.vnc_port))
                os.system("vncdo -s {}::{} type \" ks=http\" keydown shift key : "
                          "keyup shift type //10.52.249.210/esxi-kickstart.cfg pause 1 key enter"
                          .format(dest_host, nested_vm.vnc_port))

            except Exception, e:
                print "\nException caught:{}".format(e)


if __name__ == '__main__':
    sys.exit(main())