"""
Script for cluster checking configuration
you need to provide it with the path for supportconfig extracted folder
The tasks the script will do:
- find the ha.txt file
- check on the corosync configuration and check the configuration against the doc:
https://docs.microsoft.com/en-us/azure/virtual-machines/workloads/sap/high-availability-guide-suse-pacemaker#install-the-cluster
- determine the names of the nodes in the cluster
- check on the hosts file if it has the 2 nodes mentioned there
- determine the type of application in cluster is it "ASCS/ERS, NFS , SAP Hana"
- determine the type of fencing that is used:
    - in case of SBD prints the message status of the SBD devices and their configuration
    - in case of azure fence agent, check the packages version of python-azure-core, python-azure-mgmt-compute and python-azure-identity
- check on the resource definition and parameters as per our documentation and print if there is any differences for manual checking
- check on the version of resource-agents package and fence-agents package
"""

from contextvars import copy_context
from functools import total_ordering
from importlib.resources import path
import os
import logging
import subprocess
import sys
import json
import ast

f_handle = logging.FileHandler('./cluster-checker.log',mode='w')
f_format = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
f_handle.setFormatter(f_format)

logger = logging.getLogger(__name__)
logger.addHandler(f_handle)
logger.setLevel(logging.DEBUG)

def checkFileExistance(path_to_scc):
    logger.info('check for exsitence of supportconfig report itself')
    if not os.path.exists(path_to_scc):
        logger.info('The supportconfig report cannot be found')
        print('Please enter a valid path to the supportconfig report')
        return False
    #logger.info('ha.txt, network.txt, rpm.txt')
    path_to_ha = path_to_scc + '/ha.txt'
    path_to_netowrk = path_to_scc + '/network.txt'
    path_to_rpm = path_to_scc + '/rpm.txt'
    if not os.path.exists(path_to_ha) or not os.path.exists(path_to_netowrk) or not os.path.exists(path_to_rpm):
        logger.info(path_to_ha)
        logger.info(path_to_netowrk)
        logger.info(path_to_rpm)
        logger.info('Please ensure to have ha.txt, network.txt, rpm.txt avaiable in the path provided')
        print('Please ensure to have ha.txt, network.txt, rpm.txt avaiable in the path provided')
    else:
        logger.info('All files are there, ready to proceed to next step ..')
        return True
    return False


def totemChecker(path_to_scc):
    path_to_ha = path_to_scc + '/ha.txt'
    totem_cmd = 'grep  -A 18 "totem" ' + path_to_ha
    output = subprocess.Popen([totem_cmd], stdout= subprocess.PIPE, shell=True)
    totem_config = str(output.communicate()[0])
    totem_config = totem_config.replace('b\'totem ','\'')
    logger.info(f'Totem config is {totem_config}')
    totem_config = ast.literal_eval(totem_config)
    totem_config = totem_config.replace('interface', 'interface: ')
    totem_config = totem_config.replace('\tringnumber','ringnumber')
    totem_config = totem_config.replace('\tmcastport','mcastport')
    totem_config = totem_config.replace('\tttl','ttl')
    totem_config = totem_config.replace('\n}\n','\n\t}')
    totem_config = totem_config.split('\n\t')
    logger.info(totem_config)
    totem_config_dict = dict()
    for i in totem_config:
        if i.find(':') != -1:
            temp_list = i.split(':')
            if temp_list[1].strip() != '{' :
                totem_config_dict[temp_list[0]] = temp_list[1]
                logger.info(i.split(':'))
            #logger.info(i)
        #else:
        #    logger.info(i)    
    logger.info(type(totem_config_dict))
    logger.info(totem_config_dict)
    
    totem_error_list=[]
    logger.info('start checking and comparing against the documentation: https://docs.microsoft.com/en-us/azure/virtual-machines/workloads/sap/high-availability-guide-suse-pacemaker 15[A]')
    if totem_config_dict['token'].strip() != '30000':
        logger.info(f"Token value is incorrect, customer have this value {totem_config_dict['token'].strip()}")
        totem_error_list.append('token')
    if totem_config_dict['token_retransmits_before_loss_const'].strip() != '10':
        logger.info(f"Token retransmits value is incorrect, customer have this value {totem_config_dict['token_retransmits_before_loss_const'].strip()}")
        totem_error_list.append('token_retransmits_before_loss_const')
    if totem_config_dict['join'].strip() != '60':
        logger.info(f"Join value is incorrect, customer have this value {totem_config_dict['join'].strip()}")
        totem_error_list.append('join')
    if totem_config_dict['consensus'].strip() != '36000':
        logger.info(f"consensus value is incorrect, customer have this value {totem_config_dict['consensus'].strip()}")
        totem_error_list.append('consensus')
    if totem_config_dict['max_messages'].strip() != '20':
        logger.info(f"max_messages value is incorrect, customer have this value {totem_config_dict['max_messages'].strip()}")
        totem_error_list.append('max_messages')
    if totem_config_dict['transport'].strip() != 'udpu':
        logger.info(f"transport value is incorrect, customer have this value {totem_config_dict['transport'].strip()}")
        totem_error_list.append('transport')

    if len(totem_error_list) != 0:
        print(f'We found the below issues in the totem configuration of cluster, the below parameters needs to be checked {totem_error_list}')
        logger.info(f'We found the below issues in the totem configuration of cluster, the below parameters needs to be checked {totem_error_list}')
    else:
        print('Done checking on totem configuration, and no error found... proceeding further')
        logger.info('Done with totem check')


def quorumChecker(path_to_scc):
    path_to_ha = path_to_scc + '/ha.txt'
    quorum_cmd = 'grep  -A 7 "quorum {" ' + path_to_ha + ' | grep -v "#" ' 
    output = subprocess.Popen([quorum_cmd], stdout= subprocess.PIPE, shell=True)
    quorum_config = str(output.communicate()[0])
    logger.info(f'Quorum configuration is: {quorum_config}')
    quorum_config = quorum_config.replace('b\'quorum', '\'')
    quorum_config = ast.literal_eval(quorum_config)
    quorum_config = quorum_config.split('\n\t')
    quorum_config_dict = dict()
    for i in quorum_config:
        if i.find(':') != -1:
            temp_list = i.split(':')
            if temp_list[1].find('}') != -1:
                temp_list[1] = temp_list[1].strip().replace('}','')
                #logger.info(temp_list[1])
            #logger.info(temp_list[1])    
            quorum_config_dict[temp_list[0]] = temp_list[1].strip()
            #logger.info(i.split(':'))
    logger.info(quorum_config_dict)
    logger.info('start checking Quorum setting in corosync based on our documentation')
    quorom_error_list = []
    if quorum_config_dict['provider'].strip() != 'corosync_votequorum':
        logger.info(f"provider value is incorrect, customer have this value {quorum_config_dict['provider'].strip()}")
        quorom_error_list.append('provider')
    if quorum_config_dict['expected_votes'].strip() != '2':
        logger.info(f"expected_votes value is incorrect, customer have this value {quorum_config_dict['expected_votes'].strip()}")
        quorom_error_list.append('expected_votes')
    if quorum_config_dict['two_node'].strip() != '1':
        logger.info(f"two_node value is incorrect, customer have this value {quorum_config_dict['two_node'].strip()}")
        quorom_error_list.append('two_node')
    
    if len(quorom_error_list) != 0:
        print(f'We found the below issues in the Quorum configuration of cluster, the below parameters needs to be checked {quorom_error_list}')
        logger.info(f'We found the below issues in the Quorum configuration of cluster, the below parameters needs to be checked {quorom_error_list}')
    else:
        print('Done checking on Quorum configuration, and no error found... proceeding further')
        logger.info('Done with Quorum check')
    
    

if __name__ == '__main__':
    raw_args = sys.argv
    while True:
        if len(raw_args) <= 1 :
            logger.info('Please provide the path to scc report')
            path_to_scc= input('Please provide the path to scc report (either relative or absolute)')
            if path_to_scc is None or len(path_to_scc.split('/')) < 2:
                continue
            break
        else:
            path_to_scc = raw_args[1]
            break

    logger.info(path_to_scc)
    if checkFileExistance(path_to_scc):
        totemChecker(path_to_scc)
        quorumChecker(path_to_scc)



    
    


