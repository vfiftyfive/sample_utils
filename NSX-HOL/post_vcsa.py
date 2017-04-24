#!/usr/bin/env python
import sys
from nested_vsphere.utils import svc_login, create_DVS, add_host_to_VDS, add_portgroup_to_VDS, get_obj
from pyVmomi import vim
import subprocess
from pyVim.task import WaitForTask

trailer = ">>>>>>>  "

def main():


    host_list = (sys.argv[4], sys.argv[5], sys.argv[6])
    ssl_out={}
    vmnic = sys.argv[7]
    vlan_id = int(sys.argv[8])
    vlan_transit_id = int(sys.argv[9])
    i=0

    try:

        si = svc_login(host=sys.argv[1], user=sys.argv[2], port='443', password=sys.argv[3])
        content = si.content

        # Add License
        print "{}Adding Licences".format(trailer)
        content.licenseManager.AddLicense(licenseKey="MH0VM-821EP-582E9-09926-30T0Q")

        for h in host_list:
            ssl_out[i] = subprocess.check_output( "echo -n | openssl s_client -connect {}:443 2>/dev/null | "
                                                  "openssl x509 -noout -fingerprint -sha1".format(h), shell=True)\
                .split('=')[-1].strip()
            print "{}SSL Tumbprint for host {} is: {}".format(trailer, h, ssl_out[i])
            i+=1

        print "{}Creating Datacenter Object 'NSX-HOL'".format(trailer)
        dc_mo = content.rootFolder.CreateDatacenter(name='NSX-HOL')
        cluster_config_spec_mgmt = vim.cluster.ConfigSpecEx()
        mgmt_cluster_comp_res = dc_mo.hostFolder.CreateClusterEx(name='management', spec=cluster_config_spec_mgmt)

        # connect 1st host as standalone
        host_spec_1 = vim.host.ConnectSpec()
        host_spec_1.hostName = host_list[0]
        host_spec_1.userName = 'root'
        host_spec_1.password = 'VMware1!'
        host_spec_1.sslThumbprint = ssl_out[0]

        print "{}Creating cluster 'management' with host {}".format(trailer, host_list[0])
        add_host_task = mgmt_cluster_comp_res.AddHost_Task(spec=host_spec_1, asConnected=True,
                                                      license='0M0J1-CWKE0-78VP9-0KEHP-0413L')
        res = WaitForTask(add_host_task)
        print "{}status: {}".format(trailer, res)

        # connect 2nd and 3rd hosts as a cluster
        host_spec_2 = vim.host.ConnectSpec()
        host_spec_2.hostName = host_list[1]
        host_spec_2.userName = 'root'
        host_spec_2.password = 'VMware1!'
        host_spec_2.sslThumbprint = ssl_out[1]

        host_spec_3 = vim.host.ConnectSpec()
        host_spec_3.hostName = host_list[2]
        host_spec_3.userName = 'root'
        host_spec_3.password = 'VMware1!'
        host_spec_3.sslThumbprint = ssl_out[2]

        print "{}Creating cluster 'payload' with hosts {} and {}".format(trailer, host_list[1], host_list[2])
        cluster_config_spec_payload = vim.cluster.ConfigSpecEx()
        payload_cluster_comp_res = dc_mo.hostFolder.CreateClusterEx(name='payload', spec=cluster_config_spec_payload)
        add_host_task = payload_cluster_comp_res.AddHost_Task(spec=host_spec_2, asConnected=True,
                                                      license='0M0J1-CWKE0-78VP9-0KEHP-0413L')
        res = WaitForTask(add_host_task)
        print "{}Status for {}: {}".format(trailer, host_list[1], res)
        add_host_task = payload_cluster_comp_res.AddHost_Task(spec=host_spec_3, asConnected=True,
                                                      license='0M0J1-CWKE0-78VP9-0KEHP-0413L')
        res = WaitForTask(add_host_task)
        print "{}Status for {}: {}".format(trailer, host_list[2], res)

        #Create new VDS with ephemeral 'Legacy' portgroup and add hosts to it
        print "{}Creating NSX VDS ...".format(trailer)
        nsx_dvs = create_DVS(content, 'NSX-HOL', 'NSX-DVS')
        print "{}VDS {} created".format(trailer, nsx_dvs.name)
        print "{}Now adding portgroup...".format(trailer)
        portgroup_mo = add_portgroup_to_VDS(content, nsx_dvs, 'Legacy', vlan_id)
        print "{}Portgroup {} added with VLAN {}".format(trailer, portgroup_mo.name, str(vlan_id))

        #Add 'transit-ESG-CSR1k' Portgroup, to connect ESG with upstream CSR1k on VLAN 3220
        portgroup_tr_mo = add_portgroup_to_VDS(content, nsx_dvs, 'transit-ESG-CSR1k', vlan_transit_id)
        print "{}Portgroup {} added with VLAN {}".format(trailer, portgroup_tr_mo.name, vlan_transit_id)

        for i in range(5, 7):
            print "{}Adding host {} to VDS with vmnic '{}' as uplink".format(trailer, sys.argv[i], vmnic)
            host_mo = get_obj(content, [vim.HostSystem], sys.argv[i])
            add_host_to_VDS(content, host_mo, nsx_dvs, vmnic)

    except AttributeError as e:
        print "Attribute Error has occured: {}".format(e)

    except:
        raise


if __name__ == '__main__':

    sys.exit(main())
