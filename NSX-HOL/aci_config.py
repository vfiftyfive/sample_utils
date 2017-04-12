#!/usr/bin/env python
import cobra.mit.session
import cobra.mit.access
import cobra.model.fv
import cobra.model.pol
import cobra.mit.request
import sys


def main():
    session = cobra.mit.session.LoginSession('http://'+sys.argv[1], sys.argv[2], sys.argv[3])
    mo_dir = cobra.mit.access.MoDirectory(session)
    mo_dir.login()

    fv_subnet, fv_aepg =[], []
    vmm_domain_name = sys.argv[4]
    vlan_encap_list = [ i for i in range(int(sys.argv[5]), int(sys.argv[6])+1)]
    vmm_mo = mo_dir.lookupByClass('vmmDomP', propFilter='eq(vmmDomP.name,\"'+ vmm_domain_name + '\")')

    tenant_info = {
        'tenant': {'tenant_name': 'NSX-HOL'},
        'vrf': {'vrf_name': 'ctx-01'},
        'bd': {'bd_name': 'bd-default', 'ip': ['172.16.1.1/24', '172.16.2.1/24', '172.16.3.1/24', '172.16.4.1/24',
                                               '172.16.5.1/24', '172.16.6.1/24']},
        'anp': {'name': 'VTEP'},
        'epg': {'epg_name': ['s01-VTEP', 's02-VTEP', 's03-VTEP', 's04-VTEP', 's05-VTEP', 's06-VTEP']},

    }

    pol_uni = cobra.model.pol.Uni('')
    fv_tenant = cobra.model.fv.Tenant(pol_uni, name=tenant_info['tenant']['tenant_name'])
    fv_ctx = cobra.model.fv.Ctx(fv_tenant, name=tenant_info['vrf']['vrf_name'])
    fv_bd = cobra.model.fv.BD(fv_tenant, name=tenant_info['bd']['bd_name'])
    fv_rs_ctx = cobra.model.fv.RsCtx(fv_bd, tnFvCtxName=tenant_info['vrf']['vrf_name'])
    for bd_ip in tenant_info['bd']['ip']:
        fv_subnet.append(cobra.model.fv.Subnet(fv_bd, ip=bd_ip))
    fv_ap = cobra.model.fv.Ap(fv_tenant, name=tenant_info['anp']['name'])
    for e in tenant_info['epg']['epg_name']:
        fv_aepg.append(cobra.model.fv.AEPg(fv_ap, name=e))
        fv_rs_dom_att = cobra.model.fv.RsDomAtt(fv_aepg[-1], tDn=vmm_mo[0].dn, resImedcy='immediate',
                                                instrImedcy='immediate', encap='vlan-' + str(vlan_encap_list.pop(0)))
        fv_rs_bd = cobra.model.fv.RsBd(fv_aepg[-1], tnFvBDName=tenant_info['bd']['bd_name'])

    config_request = cobra.mit.request.ConfigRequest()
    config_request.addMo(fv_tenant)
    mo_dir.commit(config_request)


if __name__ == '__main__':
    sys.exit(main())