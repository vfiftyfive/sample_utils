from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import sys
import argparse
import getpass
import ssl
import atexit
import requests
import ConfigParser

def get_args():
    parser = argparse.ArgumentParser(description='Arguments required to change the network of a VM')
    parser.add_argument('-s', '--server', required=True, help='vSphere service (vCenter) to connect to')
    parser.add_argument('-o', '--port', default='443', help='Port to connect on')
    parser.add_argument('-u', '--user', required=True, help='User name to user when connecting to host')
    parser.add_argument('-p', '--password', help='Password to user when connecting to host')
    parser.add_argument('-m', '--vm', help='Name of the Virtual Machine to move')
    parser.add_argument('-n', '--network', help='Name of the destination portgroup (VSS/VDS supported)')
    args = parser.parse_args()
    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for user %s: ' %
                   (args.user))
    return args

class VM(object):
    def __init__(self, si, name):
        self.name = name
        self.si = si
        try:
            self.obj = self._get_obj(si.content, [vim.VirtualMachine], name)
        except ValueError:
            raise

    def _get_obj(self, content, vimtype, name):
        obj = None
        container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
        view = container.view
        container.Destroy()
        for v in view:
            if v.name == name:
                obj = v
                break
        if obj == None:
            raise ValueError('Object with name \'%s\'not found' % (name))
        else:
            return obj

    def _find_host(self):
        host = None
        content = self.si.content
        my_vm = self._get_obj(content, [vim.VirtualMachine], self.name)
        if my_vm:
            host = my_vm.runtime.host
        return host

    def attach_to_vswitch(self, dst_port):
        dst_host = self._find_host()
        my_net =''
        for net in dst_host.network:
            if net.name == dst_port:
                my_net = net
                break

        if not my_net:
            raise ValueError('Network \'%s\' not Found' % (dst_port))

        content = self.si.content
        vm_config_spec = vim.vm.ConfigSpec()
        device_change = vim.vm.device.VirtualDeviceSpec()
        device_list= self.obj.config.hardware.device
        nic0_device = None
        for d in device_list:
            if d.key == 4000:
                nic0_device = d
                break
        op = vim.vm.device.VirtualDeviceSpec.Operation.edit

        if "dvportgroup" in str(my_net):
            vds = self._get_obj(content, [vim.DistributedVirtualSwitch], my_net.config.distributedVirtualSwitch.name)
            net_port = vim.dvs.PortConnection()
            net_port.switchUuid = vds.uuid
            net_port.portgroupKey = my_net.key
            vnic_backing_info = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
            vnic_backing_info.port = net_port
            nic0_device.backing = vnic_backing_info
            device_change.device = nic0_device
            device_change.operation = op
            vm_config_spec.deviceChange = [device_change]
            print 'Now changing network to VDS, attaching VM \'%s\' to Portgroup \'%s\'' % (self.name, my_net.name)
            self.obj.ReconfigVM_Task(vm_config_spec)
        else:
            vnic_backing_info = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            network_obj = self._get_obj(content, [vim.Network], dst_port)
            vnic_backing_info.network = network_obj
            vnic_backing_info.deviceName = dst_port
            nic0_device.backing = vnic_backing_info
            vnic_connect_info = vim.vm.device.VirtualDevice.ConnectInfo()
            vnic_connect_info.connected = True
            vnic_connect_info.startConnected = True
            vnic_connect_info.allowGuestControl = True
            nic0_device.connectable = vnic_connect_info
            device_change.device = nic0_device
            device_change.operation = op
            vm_config_spec.deviceChange = [device_change]
            print 'Now changing network to VSS, attaching VM \'%s\' to Portgroup \'%s\'' % (self.name, my_net.name)
            self.obj.ReconfigVM_Task(vm_config_spec)

def connect_to_vc(vcenter, user, password):
    requests.packages.urllib3.disable_warnings()
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
    si = SmartConnect(host = vcenter, user = user, pwd = password, port = '443', sslContext=context)
    atexit.register(Disconnect, si)
    return si

def set_usage(file_name, args):

    if (not args.vm) & (not args.network):
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(file_name)
        try:
            vm_list = [vm.strip() for vm in config_parser.get("configuration", "vm").split(',')]
            port_group = config_parser.get("configuration", "portgroup")
        except ConfigParser.NoSectionError, e:
            raise
    else:
        vm_list = args.vm
        port_group = args.network
    return_dic = {'vm_list': vm_list, 'port_group': port_group}
    return return_dic

def main():
    args = get_args()
    si = connect_to_vc(args.server, args.user, args.password)

    try:
        get_params = set_usage('configuration.ini', args)
    except ConfigParser.NoSectionError, e:
        print 'Error when parsing \'configuration.ini\', %s' % (str(e).lower())
        sys.exit(1)
    else:
        network = get_params['port_group']
        vm_list = get_params['vm_list']

    if isinstance(vm_list, list):
        for vm_iter in vm_list:
            try:
                my_vm = VM(si, vm_iter)
            except ValueError, e:
                print e
                sys.exit(1)
            else:
                try:
                    my_vm.attach_to_vswitch(network)
                except ValueError, e:
                    print e
                    sys.exit(1)
    else:
        try:
            my_vm = VM(si, vm_list)
        except ValueError, e:
            print e
            sys.exit(1)
        else:
            try:
                my_vm.attach_to_vswitch(network)
            except ValueError, e:
                print e
                sys.exit(1)

if __name__ == '__main__':
    main()
