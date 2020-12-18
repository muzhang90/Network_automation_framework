import textfsm
from pprint import pprint
import ipaddress
from jnpr.junos import Device
import subprocess
from multiprocessing import Pool
from jnpr.junos.utils.start_shell import StartShell
from collections import Counter
from lxml import etree

import time
import warnings
import sys
#sys.stderr=open('err.txt', 'w')
warnings.filterwarnings('ignore',category=RuntimeWarning)

USER='labroot'
PASS='lab123'


'''
different approaches to collect data from the device:

1.Raw 
2.XML
'''


def gather_facts(ip: str) -> None:

    try:
        with Device(host=ip,user=USER,password=PASS) as dev:
            version = dev.rpc.get_software_information({'format': 'json'})
            host_name = version['software-information'][0]['host-name'][0]['data']
            chassis_output=dev.cli('show chassis hardware models',warning=False)


        with open('show_chassis_hardware_models.txt', 'a') as device_list_fact:
            device_list_fact.write(f'labroot@{host_name}> show chassis hardware models')
            device_list_fact.write(chassis_output)

    except ncclient.transport.errors.SSHError:
        print("\nSSH error")
    except ConnectRefusedError:
        print("\nError: Device connection refused!")
    except ConnectTimeoutError:
        print("\nError: Device connection timed out!")
    except ConnectAuthError:
        print("\nError: Authentication failure!")
    except socket.timeout():
        pass
    except Exception:
        pass

def gather_chassis_xpath(ip: str) -> None:

    with Device(host=ip, user=USER, password=PASS) as dev:
        facts = dev.facts
        hostname = facts['hostname']

        chassis_info = dev.rpc.get_chassis_inventory()
        pprint(etree.dump(chassis_info))
        chassis_models = chassis_info.findall('./chassis/chassis-module')
        with open('show_chassis_hardware_models.txt', 'a') as device_list_fact:
            for chassis_model in chassis_models:
                name = chassis_model.findtext('name')
                version = chassis_model.findtext('version')
                part_number = chassis_model.findtext('part-number')
                serial_number = chassis_model.findtext('serial-number')
                description = chassis_model.findtext('description')
                # chassis_dict.append([hostname,name,version,part_number,serial_number,description])
                device_list_fact.write(f'{hostname}, {name}, {version}, {part_number}, {serial_number}, {description}\n')


'''
Based on the data type, use different way to process the data:

1.textfsm
2.XPATH
'''

def process_textfsm(requirement,num):

    template = textfsm.TextFSM(open('juniper_show_chassis_hardware_models.textfsm'))
    with open('show_chassis_hardware_models.txt') as rfh:

        for line in rfh.readlines():
            chassis_textfsm=template.ParseText(line,eof=False)

        print(*chassis_textfsm,sep='\n')
        requirement(chassis_textfsm,num)

def process_xpath(requirement,num):
    chassis_dict = []

    with open('show_chassis_hardware_models.txt') as rfh:
        for line in rfh.readlines():
            chassis_dict.append(line.strip().split(','))
    print(chassis_dict)

    requirement(chassis_dict, num)


'''
Parsing the logs into a list, process the list with different requirement:

1.Most common used MPC card
'''


def most_common_MPC(chassis,num):
    mpc_list = []
    #print(chassis)
    for result in chassis:
        if "MPC" in result[5]:
            mpc_list.append(result[5])
    print(Counter(mpc_list).most_common(num))




'''
Utility function:

check reachibility of the provided IP range
'''


def check_reachability_multiprocessing(networks):
    pool=Pool(20)
    for network in networks:

        hosts = ipaddress.ip_network(network).hosts()

        for host in iter(hosts):
            # print(host)

            pool.apply_async(func=ping, args=(str(host),))

    pool.close()
    pool.join()


def ping(ip):
    ping_result = subprocess.call(['ping', '-c', '3', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open('Reachable_device_list.txt', 'a') as f:
        if ping_result == 0:
            f.write(ip + '\n')


'''
Data collection interface.



'''
def collect_data(gather_data,log_parsing,requirement,num):
    with open('Reachable_device_list.txt') as f:
        devices = f.readlines()

    pool = Pool(20)

    for device in devices:
        pool.apply_async(func=gather_data, args=(device.strip(),))

    pool.close()
    pool.join()

    log_parsing(requirement,num)





if __name__=='__main__':
    target_networks=input('Target networks: (please seperate by comma):\n').strip().split(',')

    '''
    10.85.160.0/24,10.85.162.0/24
    '''

    check_reachability_multiprocessing(target_networks)
    collect_data(gather_facts,process_textfsm,most_common_MPC,5)
    collect_data(gather_chassis_xpath,process_xpath,most_common_MPC,5)