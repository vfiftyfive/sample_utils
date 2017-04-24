#!/usr/bin/env python
#example script usage: /aci_config.py 1.1.1.1 admin ins3965! NSX-HOL-VMM 3201 3206 3211 3216
#1.1.1.1 is APIC IP with admin/ins3965! credentials
#NSX-HOL-VMM is the VMM domain name
#3201-3206 is a VLAN range to define explicitely encap for VMM domain bound EPGs
#3211-3216 is another VLAN range to define explicitely encap for other VMM domain bound EPGs
#This script is used to provision a tenant with the following configuration:
#  NSX-HOL (tenant)
#       |
#       VTEP (anp)
#          |
#           s01-VTEP (epg) - vlan-3201
#           s02-VTEP (epg) - vlan-3202
#           s03-VTEP (epg) - vlan-3203
#           s04-VTEP (epg) - vlan-3204
#           s05-VTEP (epg) - vlan-3205
#           s06-VTEP (epg) - vlan-3206
#           s01-transit-ESG-CSR1k (epg) - vlan-3211
#           s02-transit-ESG-CSR1k (epg) - vlan-3212
#           s03-transit-ESG-CSR1k (epg) - vlan-3213
#           s04-transit-ESG-CSR1k (epg) - vlan-3214
#           s05-transit-ESG-CSR1k (epg) - vlan-3215
#           s06-transit-ESG-CSR1k (epg) - vlan-3216
#
#
#   Networking:
#
#   ctx-01 (vrf - contracts are UNENFORCED)
#       |
#       bd-default
#               |
#               subnet 172.16.1.1/24
#               subnet 172.16.2.1/24
#               subnet 172.16.3.1/24
#               subnet 172.16.4.1/24
#               subnet 172.16.5.1/24
#               subnet 172.16.6.1/24
#
#Author: nvermand@cisco.com

import cobra.mit.session
import cobra.mit.access
import cobra.model.fv
import cobra.model.pol
import cobra.mit.request
import sys


def main():

    session = cobra.mit.session.LoginSession('http://' + sys.argv[1], sys.argv[2], sys.argv[3])
    mo_dir = cobra.mit.access.MoDirectory(session)
    mo_dir.login()

    fv_subnet, fv_aepg = [], []
    vmm_domain_name = sys.argv[4]
    vlan_encap_list = [i for i in range(int(sys.argv[5]), int(sys.argv[6])+1)]
    vlan_transit_encap_list = [i for i in range(int(sys.argv[7]), int(sys.argv[8])+1)]
    vmm_mo = mo_dir.lookupByClass('vmmDomP', propFilter='eq(vmmDomP.name,\"' + vmm_domain_name + '\")')

    tenant_info = {
        'tenant': {'tenant_name': 'NSX-HOL'},
        'vrf': {'vrf_name': 'ctx-01'},
        'bd': {'bd_name': 'bd-default', 'ip': ['172.16.1.1/24', '172.16.2.1/24', '172.16.3.1/24', '172.16.4.1/24',
                                               '172.16.5.1/24', '172.16.6.1/24']},
        'anp': {'anp_name': 'VTEP'},
        'epg': [{ 'epg_name': 's01-VTEP'}, { 'epg_name': 's02-VTEP'}, { 'epg_name': 's03-VTEP'},
                { 'epg_name': 's04-VTEP'}, {'epg_name': 's05-VTEP'}, { 'epg_name': 's06-VTEP'},
                {'epg_name': 's01-transit-ESG-CSR1k', 'encap': 'vlan-' + str(vlan_transit_encap_list[0])},
                {'epg_name': 's02-transit-ESG-CSR1k', 'encap': 'vlan-' + str(vlan_transit_encap_list[1])},
                {'epg_name': 's03-transit-ESG-CSR1k', 'encap': 'vlan-' + str(vlan_transit_encap_list[2])},
                {'epg_name': 's04-transit-ESG-CSR1k', 'encap': 'vlan-' + str(vlan_transit_encap_list[3])},
                {'epg_name': 's05-transit-ESG-CSR1k', 'encap': 'vlan-' + str(vlan_transit_encap_list[4])},
                {'epg_name': 's06-transit-ESG-CSR1k', 'encap': 'vlan-' + str(vlan_transit_encap_list[5])}]
    }

    pol_uni = cobra.model.pol.Uni('')
    fv_tenant = cobra.model.fv.Tenant(pol_uni, name=tenant_info['tenant']['tenant_name'])
    cobra.model.fv.Ctx(fv_tenant, name=tenant_info['vrf']['vrf_name'], pcEnfPref='unenforced')
    fv_bd = cobra.model.fv.BD(fv_tenant, name=tenant_info['bd']['bd_name'])
    cobra.model.fv.RsCtx(fv_bd, tnFvCtxName=tenant_info['vrf']['vrf_name'])
    for bd_ip in tenant_info['bd']['ip']:
        fv_subnet.append(cobra.model.fv.Subnet(fv_bd, ip=bd_ip))
    fv_ap = cobra.model.fv.Ap(fv_tenant, name=tenant_info['anp']['anp_name'])
    for e in tenant_info['epg']:
        fv_aepg.append(cobra.model.fv.AEPg(fv_ap, name=e['epg_name']))
        if 'encap' in e:
            res_vlan = e['encap']
        else:
            res_vlan = 'vlan-' + str(vlan_encap_list.pop(0))
        cobra.model.fv.RsDomAtt(fv_aepg[-1], tDn=vmm_mo[0].dn, resImedcy='immediate',
                                instrImedcy='immediate', encap=res_vlan)
        cobra.model.fv.RsBd(fv_aepg[-1], tnFvBDName=tenant_info['bd']['bd_name'])

    config_request = cobra.mit.request.ConfigRequest()
    config_request.addMo(fv_tenant)
    mo_dir.commit(config_request)

if __name__ == '__main__':
    sys.exit(main())
