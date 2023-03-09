#!ipython3 -i

import meraki
import copy

import os
from time import *

import asyncio
from meraki import aio
import tqdm.asyncio

import get_keys as g
import datetime
import random

import batch_helper
from bcolors import bcolors as bc

TAG_GOLDEN = 'golden'
TAG_NAMES = [ 'AVB_GROUP1', 'AVB_GROUP2', 'AVB_GROUP3', 'AVB_GROUP4' ]
TAGS = {}



log_dir = os.path.join(os.getcwd(), "Logs/")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)


#Main dashboard object
db = meraki.DashboardAPI(
            api_key=g.get_api_key(), 
            base_url='https://api.meraki.com/api/v1/', 
            output_log=True,
            log_file_prefix=os.path.basename(__file__)[:-3],
            log_path='Logs/',
            print_console=False)

#Loads whilelist from disk if it's available, otherwise the script will span ALL organizations your API key has access to
orgs_whitelist = []
file_whitelist = 'org_whitelist.txt'
if os.path.exists(file_whitelist):
    f = open(file_whitelist)
    wl_orgs = f.readlines()
    for o in wl_orgs:
        if len(o.strip()) > 0:
            orgs_whitelist.append(o.strip())

### ASYNC SECTION

async def getOrg_Networks(aio, org_id):
    result = await aio.organizations.getOrganizationNetworks(org_id,perPage=1000, total_pages='all')
    return org_id, "networks", result


async def getOrg_Devices(aio, org_id):
    result = await aio.organizations.getOrganizationDevices(org_id,perPage=1000, total_pages='all')
    return org_id, "devices", result

async def getOrg_Devices_Statuses(aio, org_id):
    result = await aio.organizations.getOrganizationDevicesStatuses(org_id,perPage=1000, total_pages='all')
    return org_id, "devices_statuses", result

async def getOrg_Devices_Inventory(aio, org_id):
    result = await aio.organizations.getOrganizationInventoryDevices(org_id,perPage=1000, total_pages='all')
    return org_id, "devices_inventory", result




async def getOrg_Licenses(aio, org_id):
    try:
        result = await aio.organizations.getOrganizationLicenses(org_id,perPage=1000, total_pages='all')
    except:
        return org_id, "license_inventory", None
    return org_id, "license_inventory", result


async def getOrg_Templates(aio, org_id):
    result = await aio.organizations.getOrganizationConfigTemplates(org_id)
    return org_id, "templates", result

async def getNetworkClients(aio, netid):
    try:
        result = await aio.networks.getNetworkClients(netid,perPage=1000,total_pages='all',timespan=86400)
    except:
        print("Whoops on Network Clients")
        result = []
    return netid, "netClients", result

async def getNetworkWirelessRfProfiles(aio, net_id):
    result = await aio.wireless.getNetworkWirelessRfProfiles(net_id)
    return net_id, "rfProfiles", result


async def getSwitchStatuses_Device(aio, serial):
    try:
        result = await aio.switch.getDeviceSwitchPortsStatuses(serial)
    except:
        print("Whoops on status")
        result = []
    return serial, "statuses", result

async def getSwitchPorts_Device(aio, serial):
    try:
        result = await aio.switch.getDeviceSwitchPorts(serial)
    except:
        print("Whoops on Ports")
        result = []
    return serial, "switchports", result

async def getNetworkApplianceVpnSiteToSiteVpn_Network(aio, net_id):
    result = await aio.network.getNetworkApplianceVpnSiteToSiteVpn(net_id)
    return netid, "VPNsit2site", result

async def getOrg_UplinkStatus(aio, org_id):
    result = await aio.organizations.getOrganizationUplinksStatuses(org_id, per_page=1000, total_pages='all')
    return org_id, "uplinkStatus", result


async def getEverything():
    async with meraki.aio.AsyncDashboardAPI(
                api_key=g.get_api_key(),
                base_url="https://api.meraki.com/api/v1",
                output_log=True,
                log_file_prefix=os.path.basename(__file__)[:-3],
                log_path='Logs/',
                maximum_concurrent_requests=10,
                maximum_retries= 100,
                nginx_429_retry_wait_time=60, 
                wait_on_rate_limit=True,
                print_console=False,
                
        ) as aio:
            orgs_raw = await aio.organizations.getOrganizations()
            orgs = {}
            for o in orgs_raw:
                if len(orgs_whitelist) == 0:
                    if o['api']['enabled']:
                        orgs[o['id']] = o
                elif o['id'] in orgs_whitelist:
                    orgs[o['id']] = o
            
            org_networks = {}
            org_devices = {}
            org_devices_statuses = {}
            org_devices_inventory = {}
            org_licenses = {}
            org_templates = {}
            org_uplinkStatus = {}
            getTasks = []
            for o in orgs:
                getTasks.append(getOrg_Networks(aio, o))
                getTasks.append(getOrg_Devices(aio, o))
                getTasks.append(getOrg_Devices_Statuses(aio, o))
                getTasks.append(getOrg_Devices_Inventory(aio,o))
                #getTasks.append(getOrg_Licenses(aio,o))
                #getTasks.append(getOrg_Templates(aio, o))
                #getTasks.append(getOrg_UplinkStatus(aio,o))

            for task in tqdm.tqdm(asyncio.as_completed(getTasks), total=len(getTasks), colour='green'):
                oid, action, result = await task
                if action == "devices":
                    org_devices[oid] = result
                elif action == "devices_statuses":
                    org_devices_statuses[oid] = result
                elif action == "devices_inventory":
                    org_devices_inventory[oid] = result
                elif action == "license_inventory":
                    org_licenses[oid] = result
                elif action == "networks":
                    org_networks[oid] = result
                elif action == "templates":
                    org_templates[oid] = result
                elif action == 'uplinkStatus':
                    org_uplinkStatus[oid] = result

            
            print("DONE")
            return org_devices, org_devices_statuses, org_devices_inventory, org_licenses, org_networks, org_templates, org_uplinkStatus
    return

async def getEverythingDevice(org_network_list):
    async with meraki.aio.AsyncDashboardAPI(
                api_key=g.get_api_key(),
                base_url="https://api.meraki.com/api/v1",
                output_log=True,
                log_file_prefix=os.path.basename(__file__)[:-3],
                log_path='Logs/',
                maximum_concurrent_requests=10,
                maximum_retries= 100,
                wait_on_rate_limit=True,
                print_console=False,
                
        ) as aio:
            getTasks = []
            switches_statuses = {}
            switches_switchports = {}
            for oid_tmp in org_network_list:
                device_list = org_devices[oid_tmp]
                if len(device_list) == 0: 
                    print(f"No devices in [{oid_tmp}] Length[{len(device_list)}]")
                    continue
                if not oid_tmp in switches_switchports: switches_switchports[oid_tmp] = {}
                if not oid_tmp in switches_statuses: switches_statuses[oid_tmp] = {}
                
                for d in device_list:
                    if not is_DeviceOnline(d['serial']): 
                        #print(f"Device[{d['serial']}] is offline")
                        continue
                    
                    if d['productType'] == 'switch':
                        print(f"DEVICE ONLINE[{d['serial']}]")
                        getTasks.append(getSwitchPorts_Device(aio, d['serial']))
                        #getTasks.append(getSwitchStatuses_Device(aio, d['serial']))
                        print("DONE!")
                    if False:
                        print()

                for task in tqdm.tqdm(asyncio.as_completed(getTasks), total=len(getTasks), colour='green'):
                    serial, action, result2 = await task
                    if action == 'statuses':
                        switches_statuses[oid_tmp][serial] = result2
                    elif action == 'switchports':
                        switches_switchports[oid_tmp][serial] = result2
                    
            
            print("DONE")
            return switches_switchports, switches_statuses

async def getEverythingNetwork(org_network_list):
    async with meraki.aio.AsyncDashboardAPI(
                api_key=g.get_api_key(),
                base_url="https://api.meraki.com/api/v1",
                output_log=True,
                log_file_prefix=os.path.basename(__file__)[:-3],
                log_path='Logs/',
                maximum_concurrent_requests=10,
                maximum_retries= 100,
                wait_on_rate_limit=True,
                print_console=False,
                
        ) as aio:
            getTasks = []
            for o in org_network_list:
                network_list = org_network_list[o]
                for net in network_list:
                    #print(net)
                    getTasks.append(getNetworkClients(aio, net['id']))
                    if 'wireless' in net['productTypes']:
                        getTasks.append(getNetworkWirelessRfProfiles(aio,net['id']))
                    
            network_clients = {}
            network_rfp = {}
            for task in tqdm.tqdm(asyncio.as_completed(getTasks), total=len(getTasks), colour='green'):
                netid, action, result = await task
                if action == 'netClients':
                    network_clients[netid] = result
                elif action == 'rfProfiles':
                    network_rfp[netid] = result
                    
                
            
            print("DONE")
            return network_clients, network_rfp


### /ASYNC SECTION   



### TOOLS SECTION

def getDevice(serial):
    for o in org_devices:
        devs = org_devices[o]
        for d in devs:
            if serial == d['serial']:
                return d
    return

def getNetwork(netID):
    for o in org_networks:
        nets = org_networks[o]
        for n in nets:
            if netID == n['id']:
                return n
    return

def getOrg(orgID):
    for o in orgs:
        if orgID == o['id']:
            return o
    return

#returns true if the device is found to be online
def is_DeviceOnline(serial):
    for oid in org_devices_statuses:
        devs = org_devices_statuses[oid]
        for dev in devs:
            if serial == dev['serial']:
                online_states = ['online']#, 'alerting']
                if dev['status'] in online_states:
                    return True
                else:
                    return False

#same as compare() but strips out ID/networkID for profiles/group policies etc
def soft_compare(A, B):
    t_A = copy.deepcopy(A)
    t_B = copy.deepcopy(B)
    delete_keys1 = ['id', 'networkId', 'groupPolicyId', 'dnsRewrite', 'adultContentFilteringEnabled', 'roles'] # 'radiusServerTimeout', 'radiusServerAttemptsLimit', 'radiusFallbackEnabled', 'radiusAccountingInterimInterval' ]
    for dk in delete_keys1:
        if dk in t_A: t_A.pop(dk)
        if dk in t_B: t_B.pop(dk)

    #This bit of code should "true up" both objects by removing uncomming keys, similar to the static removal of keys above, but dynamic
    toRemove = []
    if len(t_A) > len(t_B) and len(t_B) > 0:
        for k in t_A:
            if not k in t_B:
                toRemove.append(k)
        for tr in toRemove:
            if not type(tr) == dict: t_A.pop(tr)
    elif len(t_B) > len(t_A) and len(t_A) > 0:
        for k in t_B:
            if not k in t_A:
                toRemove.append(k)
        for tr in toRemove:
            if not type(tr) == dict: t_B.pop(tr)

    if not len(t_A) == len(t_B):
        print("Both objects aren't equal.... somethings wrong...")


    delete_keys2 = [ 'id', 'radsecEnabled' , 'openRoamingCertificateId', 'caCertificate']
    #had to add some logic to pop the "id" and "radsecEnabled". 'id' is unique and 'radsecEnabled' is beta for openroaming
    if 'radiusServers' in t_A:
        for radServ in t_A['radiusServers']:
            for dk in delete_keys2:
                if dk in radServ: radServ.pop(dk)
            #radServ.pop('id')
            #if 'radsecEnabled' in radServ: radServ.pop('radsecEnabled')
        #t_A['radiusServers'][0].pop('id')
        #if 'radsecEnabled' in t_A['radiusServers'][0]: t_A['radiusServers'][0].pop('radsecEnabled')

    if 'radiusAccountingServers' in t_A: 
        for radACC in t_A['radiusAccountingServers']:
            for dk in delete_keys2:
                if dk in radACC: radACC.pop(dk)   

    if 'radiusServers' in t_B:
        for radServ in t_B['radiusServers']:
            for dk in delete_keys2:
                if dk in radServ: radServ.pop(dk)

    if 'radiusAccountingServers' in t_B:
        for radACC in t_B['radiusAccountingServers']:
            for dk in delete_keys2:
                if dk in radACC: radACC.pop(dk) 
        
    result = compare(t_A, t_B)
    if not result:
        a = 0 #really just a placeholder for breakpoint
    return result

 #compares JSON objects, directionarys and unordered lists will be equal 
def compare(A, B):
    result = True
    if A == None and B == None: 
        return True

    if A == B:
        return True

    if not type(A) == type(B): 
        #print(f"Wrong type")
        return False

    #try:
    
    if not type(A) == int and not type(A) == str and not type(A) == float and not type(A) == bool and not type(A) == dict and not type(A) == list: 
        print(f'Wierd Compare type of [{type(A)}] Contents[{A}]')
        return False
    
    #except:
    #    print()
    
    if type(A) == dict:
        for a in A:
            #if a in B and not self.compare(A[a],B[a]):
            #    return False
            result = compare(A[a],B[a])
            if a in B and not compare(A[a],B[a]):
                #print(f"False {A} {B}")
                return False
    elif type(A) == list:
        found = 0
        for a in A:
            if type(a) == dict:
                for b in B:
                    if compare(a,b):
                        found += 1
            #elif A == B:
                #return True
            elif not a in B:
                #print(f"False {A} {B}")
                return False
        #if found == len(A) and len(A) > 0:
            #print("YEAH")
        if A == B:
            return True
        elif not found == len(A):
            print(f"False {A} {B}")
            return False             
        
    else:
        if not A == B:
            print(f"False {A} {B}")
            return False
    #if 'name' in A and 'number' in A:
    #    print()  
    return result
##END-OF COMPARE

#splits a list into chucks, returns list object
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

#re-wrote this to support dictionaries or lists
def findName(list_of_things, target_name):
    res = []
    if type(list_of_things) == list:
        for thing in list_of_things:
            if target_name in thing['name']:
                res.append(thing)
        return res

    elif type(list_of_things) == dict: #it's a list, make it a dict
        for o in list_of_things:
            stuffs = list_of_things[o]
            for s in stuffs:
                #print(f"Looking for [{target_name}] in [{s['name']}]")
                if target_name in s['name']:
                    res.append(s)
        return res
    

ex_arr = ['id', 'networkId']
def stripJSON(input_list, exclude_arr):
    for k in ex_arr:
        if type(input_list) == list:
            for t_dict in input_list:
                print(t_dict['name'])
                if k in t_dict: t_dict.pop(k)
                
        elif type(input_list) == dict:
            if k in input_list: input_list.pop(k)
        else:
            print(f"Stripping issue, input_list was {type(input_list)}")
    return input_list
            
def compare_RFP(rfp_A, rfp_B):
    result = True
    if type(rfp_A) == list and type(rfp_B) == list:
        for A in rfp_A:
            A_name = A['name']
            B = findName(rfp_B,A_name)
            if len(B) > 1:
                print(f"Something went wrong, {A_name} returned multiple results total[{len(b)}]")
            elif len(B) == 1: 
                B = B[0]
                result = soft_compare(A,B)
            else:
                print(f"No matching RFP name[{A_name}]")
                result = False
    
    return result
### /END OF TOOLS SECTION


### DATA GATHERING 
orgs = db.organizations.getOrganizations()

# This section returns all Devices, Networks and Templates in all the orgs you have access to
start_time = time()
org_devices, org_devices_statuses, org_devices_inventory, org_licenses, org_networks, org_templates, org_uplinkStatus = asyncio.run(getEverything())
network_clients, network_rfp = asyncio.run(getEverythingNetwork(org_networks)) #this needs {org:networks[]} format
end_time = time()
elapsed_time = round(end_time-start_time,2)

print(f"Loaded Devices/Networks/Licenses/Templates took [{elapsed_time}] seconds")
print()
# end-of Devices/Networks/Templates

# This section returns all switchport config and status
start_time = time()
org_switches_switchports, org_switches_statuses = asyncio.run(getEverythingDevice(org_networks))
end_time = time()
elapsed_time = round(end_time-start_time,2)

print(f"Loaded Switches took [{elapsed_time}] seconds")
print()
# end-of Devices/Networks/Templates

### /END DATA GATHERING 


#this is for testing from iPython/interactive mode
db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', maximum_retries=50, print_console=False)

orgs = db.organizations.getOrganizations()

org_id = ''

toys = ["org_devices","org_devices_statuses", "org_devices_inventory", "org_licenses", "org_networks", "org_templates", "org_uplinkStatus", "org_switches_switchports", "org_switches_statuses"]
print()
print(f"The following objects are available to play with, run <obj>.keys() to find the OrgIDs and then reference <obj>[org_id] to get that orgs data")
print(toys)
print()

