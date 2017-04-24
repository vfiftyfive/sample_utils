#!/bin/bash
#usage: ./nsx-hol.sh x, where x is the number of students

#################INIT VARIABLES#################
trailer='>>>>>>> '
#Setting env
export ESXI_PWD='Cisco123'
if [ $# -eq 0 ]; then
	nbr_student=1
else
	nbr_student="$1"
fi
export HOST='10.48.58.109'
export USER='cpaggen'
export PASSWORD='ins3965!'
export VMNAME_LIST="student-1-vesx-01,student-1-vesx-02,student-1-vesx-03"

if [ -n  "$nbr_student" ]; then
	if [ "$nbr_student" -gt 1 ]; then
		for i in $(seq 2 "${nbr_student}"); do
			VMNAME_LIST=${VMNAME_LIST}",student-${i}-vesx-01,student-${i}-vesx-02,student-${i}-vesx-03"
		done
	fi
fi

#Create multiple lists, ie. 1 per student based on a flat list containing all VMs. 3 VMs are allocated per student, so each list will contain 3 VMs. The name of the list is "host_list_n" where n is the student number
export VLAN_MIN=3201
export VLAN_MAX=3209
declare -a vlan_id
for i in $(seq 1 "${nbr_student}"); do
	count=0
	if [ ${VLAN_MIN} -le ${VLAN_MAX} ]; then
		vlan_id[$i-1]=${VLAN_MIN}
		((VLAN_MIN++))
	fi
	while [ ${count} -le 2 ]; do
		((index=count+1))
		eval "host_list_${i}[${count}]=student-${i}-vesx-0${index}"
		((count++))
	done
done

export COMPUTE_HOSTS='10.48.58.110,10.48.58.111'
export DATASTORE='Nimble-Lun-11'
export VMFOLDER='vesxi'
export NETWORK='NSX-HOL|VTEP|s01-VTEP'
export MGMT_NETWORK='Backbone'
export ISO='[Nimble-Lun-11] Sources/VMware-VMvisor-Installer-6.0.0.update03-5050593.x86_64.iso'
export MEM=16384
export VCPU=4
export GUESTID='vmkernel5guest'
export VMX_VERSION='vmx-10'
export DISK_SIZE=80
vmnic='vmnic2'

compute_hosts=$(echo -e ${COMPUTE_HOSTS} | tr ',' "\n")
sshpass_cmd="/usr/bin/sshpass -p $ESXI_PWD"
###################################################

# Get IP of nested hosts
function get_VM_IP {
	for host in ${compute_hosts}; do
  	match_vm=$(sshpass -p Cisco123 ssh -o StrictHostKeyChecking=no root@${host} "esxcli network vm list | awk '/$1/ {print \$1}' | xargs -0 esxcli network vm port list -w | awk '/IP Address: 1/ {print \$3}'")
    if [ ! -z "$match_vm" ]; then
      break
    fi
	done
	echo -e ${match_vm}
}

#Creating VMs
/usr/bin/env python ./main.py

# Enable VM IP discovery on ARP
for host in ${compute_hosts}; do
	echo -e ${trailer} "Setting GuestIPHack on host $host"
	${sshpass_cmd} ssh -o StrictHostKeyChecking=no root@"${host}" esxcli system settings advanced set -o /Net/GuestIPHack -i 1

# Allowing VNC on ESXi FW
	echo -e ${trailer} "Adding VNC in ESXi firewall on host $host"
	${sshpass_cmd} scp root@${host}:/etc/vmware/firewall/service.xml ./service.xml."${host}"
	fw_pol=$(grep -E '<id>vnc</id>' ./service.xml."${host}")
	if [ -z "$fw_pol" ]; then
 		sed -i "s/<\/ConfigRoot>//" ./service.xml."${host}"
		echo -e "
  		<service id='0033'>
    		<id>vnc</id>
    		<rule id='0000'>
    	  		<direction>inbound</direction>
      			<protocol>tcp</protocol>
      			<porttype>dst</porttype>
      			<port>
        			<begin>5900</begin>
        			<end>6000</end>
      			</port>
    		</rule>
    		<enabled>true</enabled>
    		<required>false</required>
  		</service>
		</ConfigRoot>" >> ./service.xml.${host}
	 	${sshpass_cmd} scp ./service.xml."${host}" root@"${host}":/etc/vmware/firewall/
	 	${sshpass_cmd} ssh -o StrictHostKeyChecking=no root@"${host}" mv /etc/vmware/firewall/service.xml /etc/vmware/firewall/service.xml.old
 		${sshpass_cmd} ssh -o StrictHostKeyChecking=no root@"${host}" mv /etc/vmware/firewall/service.xml.${host} /etc/vmware/firewall/service.xml
 		${sshpass_cmd} ssh -o StrictHostKeyChecking=no root@"${host}" esxcli network firewall refresh
 		${sshpass_cmd} ssh -o StrictHostKeyChecking=no root@"${host}" 'if [ ! -d /store/firewall ]; then mkdir /store/firewall; fi'
 		${sshpass_cmd} ssh -o StrictHostKeyChecking=no root@"${host}" cp /etc/vmware/firewall/service.xml /store/firewall/service.xml
#		$sshpass_cmd ssh -o StrictHostKeyChecking=no root@${host} 'sed -i "s/exit 0//" /etc/rc.local.d/local.sh'
#        $sshpass_cmd ssh -o StrictHostKeyChecking=no root@${host} 'echo -e "
#        cp /store/firewall/service.xml /etc/vmware/firewall/service.xml
# 	 	esxcli network firewall refresh
# 	 	exit 0" >> /etc/rc.local.d/local.sh'
	fi
done

sleep 300

# Save IP of nested hosts in individual table, 1 per student - res_n where n is the student number
for i in $(seq 1 ${nbr_student}); do
	j=0
	var_host_list="host_list_${i}[@]"
	for v in "${!var_host_list}"; do
		eval "res_${i}[$j]=$(get_VM_IP ${v})"
		res="res_${i}[$j]"
		ssh-keygen -R ${!res}
		#Enable IP discovery on nested hosts
		echo -e "${trailer}" "Setting GuestIPHack on host ${!res}"
		sshpass -p VMware1! ssh -o StrictHostKeyChecking=no root@${!res} esxcli system settings advanced set -o /Net/GuestIPHack -i 1
		((j++))
	done
done

#Find IP of the nested host that will host vCenter
for i in $(seq 1 ${nbr_student}); do
	host_0="res_${i}[0]"
	vcenter_host[$i-1]=${!host_0}
	echo -e "host with vCenter is ${!host_0} for student $i"
done

#################INIT OVFTOOL VARIABLES#################
OVFTOOL="/usr/bin/ovftool"
VCSA_OVA="http://fms01.uktme.cisco.com/VMWare/vSphere6/vCenter/vmware-vcsa"
TRUSTY_OVA="http://fms01.uktme.cisco.com/Ubuntu/Ubuntu-Trusty-Mini-v1.3/Ubuntu-Trusty-Mini-v1.3.ovf"
NSXM_OVA="http://fms01.uktme.cisco.com/VMWare/NSX/6.3/OVF/VMware-NSX-Manager-6.3.1-5124716.ovf"

ESXI_USERNAME=root
ESXI_PASSWORD=VMware1!
VM_NETWORK="VM Network"
VM_LEGACY="Legacy"

# Configurations for VC Management Node
VCSA_VMNAME=vcsa
VCSA_ROOT_PASSWORD=VMware1!
VCSA_NETWORK_MODE=dhcp
#Same value as VCSA_IP if no DNS
VCSA_ENABLE_SSH=True
VCSA_DEPLOYMENT_SIZE=tiny

# Configuration for SSO
SSO_DOMAIN_NAME=cisco.local
SSO_SITE_NAME=cisco
SSO_ADMIN_PASSWORD=VMware1!

# NTP Servers
NTP_SERVERS=0.pool.ntp.org

#Configuration for NSX Manager Node
NSXM_NAME=nsxmgr
NSXM_PWD=VMware1!

###################################################

#Check ovftool version
"${OVFTOOL}" --version | grep '4.1.0' > /dev/null 2>&1
if [ $? -eq 1 ]; then
	echo -e "This script requires ovftool 4.1.0 ..."
	exit 1
fi

#Deploy vCenter for every student
i=0
for esxi_host in "${vcenter_host[@]}"; do

	#use OVFTOOL to deploy VCSA
	echo -e "\n$trailer" "Deploying vCenter Server Appliance Embedded w/PSC ${VCSA_VMNAME} ..."
	"${OVFTOOL}" --acceptAllEulas --noSSLVerify --skipManifestCheck --X:injectOvfEnv --allowExtraConfig --X:enableHiddenProperties --X:waitForIp --sourceType=OVA --powerOn \
	"--net:Network 1=${VM_NETWORK}" --datastore=${esxi_host}-local-storage-1 --diskMode=thin --name=${VCSA_VMNAME} \
	"--deploymentOption=${VCSA_DEPLOYMENT_SIZE}" \
	"--prop:guestinfo.cis.vmdir.domain-name=${SSO_DOMAIN_NAME}" \
	"--prop:guestinfo.cis.vmdir.site-name=${SSO_SITE_NAME}" \
	"--prop:guestinfo.cis.vmdir.password=${SSO_ADMIN_PASSWORD}" \
	"--prop:guestinfo.cis.appliance.net.mode=${VCSA_NETWORK_MODE}" \
	"--prop:guestinfo.cis.appliance.root.passwd=${VCSA_ROOT_PASSWORD}" \
	"--prop:guestinfo.cis.appliance.ssh.enabled=${VCSA_ENABLE_SSH}" \
	"--prop:guestinfo.cis.appliance.ntp.servers=${NTP_SERVERS}" \
	${VCSA_OVA} "vi://${ESXI_USERNAME}:${ESXI_PASSWORD}@${esxi_host}/"

	#get IP Address of vCenter
	declare -a vcenter_ip
	while [ -z "${vcenter_ip[$i]}" ]; do
		vcenter_ip[$i]=$(sshpass -p 'VMware1!' ssh -o StrictHostKeyChecking=no root@${esxi_host} "esxcli network vm list | awk '/${VCSA_VMNAME}/ {print \$1}' | xargs -0 esxcli network vm port list -w | awk '/IP Address: 1/ {print \$3}'")
	done
	echo -e "vCenter IP address received by script is ${vcenter_ip[$i]}"

	#use OVFTOOL to deploy NSX Manager
	echo -e "\n$trailer" "Deploying NSX Manager ${NSXM_NAME} ..."
	"${OVFTOOL}" --acceptAllEulas --noSSLVerify --skipManifestCheck --X:injectOvfEnv --allowExtraConfig --X:waitForIp --X:enableHiddenProperties --sourceType=OVF --powerOn \
	"--net:VSMgmt=${VM_NETWORK}" \
	"--datastore=${esxi_host}-local-storage-1" \
	--diskMode=thin --name=${NSXM_NAME}\
	"--prop:vsm_cli_passwd_0=${NSXM_PWD}" \
	"--prop:vsm_cli_en_passwd_0=${NSXM_PWD}" \
	"--prop:vsm_hostname=${NSXM_NAME}" \
	"--prop:vsm_ntp_0=${NTP_SERVERS}" \
	"--prop:vsm_isSSHEnabled=True" \
	${NSXM_OVA} "vi://${ESXI_USERNAME}:${ESXI_PASSWORD}@${esxi_host}/"

	echo -e "Checking to see if the VCSA endpoint https://${vcenter_ip[$i]}/ is ready ..."
	until [[ $(curl --connect-timeout 30 -s -o /dev/null -w "%{http_code}" -i -k https://${vcenter_ip[$i]}/) -eq 200 ]]; do
		echo -e "Not ready, sleeping for 60sec"
		sleep 60
	done
	echo -e "VCSA Embedded Node (${vcenter_ip[$i]}) is now ready!"
	((i++))
done

    #add hosts to vCenter inventory for every student
	echo -e "Now processing post vCenter deployment tasks...please wait"
	for i in $(seq 1 ${nbr_student}); do
		var_host_res="res_${i}[@]"
		echo -e "For student $i, vCenter IP is ${vcenter_ip[$i-1]}, IP of nested hosts are: ${!var_host_res}"
		echo -e "Now adding compute resources to vCenter..."
		/usr/bin/env python ./post_vcsa.py ${vcenter_ip[$i-1]} administrator@${SSO_DOMAIN_NAME} ${VCSA_ROOT_PASSWORD} ${!var_host_res} ${vmnic} ${vlan_id[$i-1]} $((${vlan_id[$i-1]} + 10))
	done

	#Use OVFTOOL to deploy VM Ubuntu images on student-n-02
     for i in $(seq 1 ${nbr_student}); do
        host_1="res_${i}[1]"
        var_host_res="res_${i}[@]"
            for j in {1..3}; do
                echo -e "\n$trailer" "Deploying VM Ubuntu images on host ${!host_1} ..."
                "${OVFTOOL}" --acceptAllEulas --noSSLVerify --sourceType=OVF --X:injectOvfEnv --powerOn \
                "--net:bridged=${VM_LEGACY}" "--net:custom=${VM_LEGACY}" \
                "--datastore=${!host_1}-local-storage-1" \
                --diskMode=thin --name=nsxhol-vm-0${j} \
                ${TRUSTY_OVA} "vi://${ESXI_USERNAME}:${ESXI_PASSWORD}@${!host_1}/"
            done
     done

	#Use OVFTOOL to deploy VM Ubuntu images on student-n-03
	for i in $(seq 1 ${nbr_student}); do
        host_2="res_${i}[2]"
            for j in {1..3}; do
                echo -e "\n$trailer" "Deploying VM Ubuntu images on host ${!host_2} ..."
                "${OVFTOOL}" --acceptAllEulas --noSSLVerify --sourceType=OVF --X:injectOvfEnv --powerOn \
                "--net:bridged=${VM_LEGACY}" "--net:custom=${VM_LEGACY}" \
                "--datastore=${!host_2}-local-storage-1" \
                --diskMode=thin --name=nsxhol-vm-1${j} \
                ${TRUSTY_OVA} "vi://${ESXI_USERNAME}:${ESXI_PASSWORD}@${!host_2}/"
            done
    done
