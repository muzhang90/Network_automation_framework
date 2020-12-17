import textfsm
from pprint import pprint
import ipaddress
from jnpr.junos import Device
import subprocess
from multiprocessing import Pool
from jnpr.junos.utils.start_shell import StartShell
from collections import Counter
import time
import warnings
import sys
sys.stderr=open('err.txt','w')
warnings.filterwarnings('ignore',category=RuntimeWarning)

USER='labroot'
PASS='lab123'





def gather_facts(ip):

    try:
        with Device(host=ip,user=USER,password=PASS) as dev:
            version = dev.rpc.get_software_information({'format': 'json'})
            host_name = version['software-information'][0]['host-name'][0]['data']
            chassis_output=dev.cli('show chassis hardware models',warning=False)


        with open('show_chassis_hardware_models.txt','a') as device_list_fact:
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



def process_textfsm(requirement,num):

    template = textfsm.TextFSM(open('juniper_show_chassis_hardware_models.textfsm'))
    with open('show_chassis_hardware_models.txt') as rfh:

        for line in rfh.readlines():
            chassis_textfsm=template.ParseText(line,eof=False)

        print(*chassis_textfsm,sep='\n')
        requirement(chassis_textfsm,num)

def most_common_MPC(chassis,num):
    mpc_list = []

    for result in chassis:
        if "MPC" in result[5]:
            mpc_list.append(result[5])
    print(Counter(mpc_list).most_common(num))







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