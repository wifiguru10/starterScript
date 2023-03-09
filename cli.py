#!ipython3 -i 

import meraki
import copy
import os
import pickle
import get_keys as g
import random
import sys
import datetime
from time import *

def findName(list_of_things, target_name):
    res = []
    for o in list_of_things:
        if target_name in o['name']:
            res.append(o)
    return res

db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', maximum_retries=50, print_console=False)

orgs = db.organizations.getOrganizations()

org_id = '121177'

nix = findName(orgs, "Nix")

devs = db.organizations.getOrganizationDevices(org_id)


# TODO: Test....

# TODO: inspected.stack() - inter tools - https://docs.python.org/3/library/itertools.html

# TODO: GPC - https://developer.cisco.com/meraki/api-v1/#!get-device-switch-ports-statuses
