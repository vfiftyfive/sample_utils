#!/usr/bin/env python
import sys
from pyVim.connect import SmartConnect, Disconnect
import requests
import atexit
import ssl

host = ['10.48.58.83', '10.48.58.86', '10.48.58.93', '10.48.58.95','10.48.58.97']
user = 'administrator@cisco.local'
password ='VMware1!'
port = 443

def main():

    requests.packages.urllib3.disable_warnings()
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.verify_mode = ssl.CERT_NONE
    for h in host:
        si = SmartConnect(host=h, user=user, pwd=password, port=port, sslContext=context)
        atexit.register(Disconnect, si)
        content = si.content
        print "Adding NSX Licences on vCenter {}".format(h)
        content.licenseManager.AddLicense(licenseKey="MH0VM-821EP-582E9-09926-30T0Q")

if __name__ == '__main__':
    sys.exit(main())