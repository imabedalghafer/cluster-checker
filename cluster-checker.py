#!dev/bin/python
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

import os
import logging
import subprocess
import sys
import xml.etree.ElementTree as ET
from xml import etree
import ast
#from telemtry import collect_sr, log_case_scc

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

def rpmChecker(path_to_scc, version_id, azure_fence_agent, sbd_fence_agent):
    logger.info('Start checking the installed packages for any known issues..')
    path_to_rpm = path_to_scc + '/rpm.txt'
    if version_id.split('.')[0] == "12":
        packages_list = {'fence-agents':4.4 ,'python-azure-mgmt-compute': 17.0, 'python-azure-identity' : 1.0 ,'cloud-netconfig-azure': 1.3 ,'resource-agents': 4.3,'python-azure-core': [1.9, 1.22] }
    if version_id.split('.')[0] == "15":
        #packages_list = ['fence-agents','python3-azure-mgmt-compute','python3-azure-identity','cloud-netconfig-azure','resource-agents','python3-azure-core']
        packages_list = {'fence-agents':4.4 ,'python3-azure-mgmt-compute': 17.0, 'python3-azure-identity' : 1.0 ,'cloud-netconfig-azure': 1.3 ,'resource-agents': 4.3,'python3-azure-core': [1.9, 1.22] }
    logger.info(f'Check for the following packages {packages_list.keys()}')
    missing_rpms = []
    not_correct_version = []
    for i in packages_list.keys():
        rpm_find_cmd = 'grep '+ i + ' ' + path_to_rpm + ' | head -1  | awk \'{print $NF}\''
        output = subprocess.Popen([rpm_find_cmd], stdout=subprocess.PIPE, shell=True)
        rpm_version = str(output.communicate()[0])
        rpm_version = rpm_version.replace('b\'','')
        rpm_version = rpm_version.replace('\'','')
        rpm_version = rpm_version.replace('\\n','')
        if len(rpm_version) != 0:
            #rpm_version = rpm_version[0] + rpm_version[1] + rpm_version[2]
            rpm_version_list = rpm_version.split('.')
            #logger.info(rpm_version_list)
            if rpm_version_list[1].find('-'):
                rpm_version_list[1] = rpm_version_list[1].split('-')[0]
            rpm_version = float(rpm_version_list[0] + '.' + rpm_version_list[1])
            logger.info(f'{i} has version {rpm_version}')
            if not isinstance(packages_list[i], float):
                if rpm_version == packages_list[i][0] or rpm_version > packages_list[i][1]:
                    logger.info(f'package {i} is good, with version {rpm_version}')
                else:
                    logger.info(f'package {i} is not on a good version, it has a version {rpm_version} while it should either {packages_list[i][0]} or greater than {packages_list[i][1]}')
                    not_correct_version.append(i)
            else:
                if rpm_version >= packages_list[i]:
                    logger.info(f'package {i} is good, with version {rpm_version}')
                else:
                    logger.info(f'package {i} is not on a good version, it has a version {rpm_version} while it should had {packages_list[i]}')
                    not_correct_version.append(i)
        else:
            logger.info(f'{i} is not installed on system')
            missing_rpms.append(i)

    if azure_fence_agent == 1 and (len(missing_rpms) != 0 or len(not_correct_version) != 0):
        logger.info('Customer has fence agent, please consider the python packages mentioned')
        print('Customer has fence agent, please consider the python packages mentioned')
        logger.info(f'The missing packages are {missing_rpms}')
        print(f'The missing packages are {missing_rpms}')
        logger.info(f'Packages with incorrect versions are {not_correct_version}')
        print(f'Packages with incorrect versions are {not_correct_version}')
        #cluster_config = readingCib(path_to_scc)
        #resources_config = cluster_config[2]
        #logger.info(resources_config.getchildren())
        #has_fence_agent = 0
        #for i in resources_config:
        #    logger.info(i.attrib)
        #    if  i.attrib.has_key('type'):
        #        if i.attrib['type'] == 'fence_azure_arm' :
        #            has_fence_agent = 1
        #            break
        #if has_fence_agent:
        #    logger.info('Customer has fence agent, please consider the python packages mentioned')
        #    print('Customer has fence agent, please consider the python packages mentioned')
        #else:    
        #    logger.info('Customer does not have fence agent configured, please ignore the python packages mentioned.')
        #    print('Customer does not have fence agent configured, please ignore the python packages mentioned.')
    else:
        logger.info('Done checking on rpms and everything is fine..')
        print('Done checking on rpms and everything is fine..')
        

def osVersion(path_to_scc):
    logger.info('Checking for the basic-environment.txt file')
    file_path = path_to_scc + '/basic-environment.txt'
    cmd = 'grep VERSION_ID ' + file_path + ' | cut -d "=" -f 2'
    output = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    version_id = str(output.communicate()[0])
    version_id = version_id.replace('b\'','\'')
    version_id = version_id.replace('\\n','')
    version_id = version_id.replace('\"','')
    version_id = ast.literal_eval(version_id)
    version_id = str(version_id)
    logger.info(f'The OS version is: {version_id}')
    return version_id


def readingCib(path_to_scc):
    from lxml import etree # imported to use the enhanced parser in this library.
    path_to_ha = path_to_scc + '/ha.txt'
    get_generate_cib_command = "sed -ne '/^\# \/var\/lib\/pacemaker\/cib\/cib.xml$/{:a' -e 'n;p;ba' -e '}' " + path_to_ha + " | sed '1,/\#==/!d' | grep -v '#==' > ./cib.xml"
    output = subprocess.Popen([get_generate_cib_command], stdout=subprocess.PIPE, shell=True)
    logger.info(str(output.communicate()))
    path_to_xml = './cib.xml'
    parser = etree.XMLParser(recover=True)
    mycib = ET.parse(path_to_xml,parser=parser)
    return mycib.getroot()[0]
    #logger.info(mycib.getroot()[0].attrib)

def propertyChecker(root_xml):
    root = root_xml
    logger.info(root)
    cluster_property = root[0][0]
    logger.info(cluster_property)
    for i in cluster_property:
        if i.attrib['name'] == 'stonith-enabled':
            logger.info(f'Customer has stonith-enabled set to: {i.attrib["value"]}')
            if i.attrib["value"] == 'true':
                print(f'Customer has stonith-enabled set to: {i.attrib["value"]}')
            else:
                print('\033[91m'+f'Customer has stonith-enabled set to: {i.attrib["value"]}' + '\033[0m')
                print('\033[91m' + 'Please note that stonith-enabled=false cluster are not supported configuration as per the documentation https://documentation.suse.com/sle-ha/15-SP1/html/SLE-HA-all/cha-ha-fencing.html#sec-ha-fencing-recommend'+'\033[0m')
                quit()
        

    node_list = []
    node_list_xml = root[1]
    azure_fence_agent = sbd_fence_agent = 0
    
    for  i in node_list_xml:
        node_list.append(i.attrib['uname'])
    
    logger.info(f'Customer has the below nodes as part of cluster: {node_list}')
    print(f'Customer has the below nodes as part of cluster: {node_list}')

    cluster_resources = root[2]
    fencing_resources = []
    for i in cluster_resources:
        if i.attrib.has_key('type'):
            if i.attrib['type'] == 'fence_azure_arm':
                fencing_resources.append('azure_fence_agent')
                azure_fence_agent = 1
            if i.attrib['type'] == 'external/sbd':
                fencing_resources.append('sbd')
                sbd_fence_agent = 1
    
    logger.info(f'Customer has the below fencing mechanism configured: {fencing_resources}')
    print(f'Customer has the below fencing mechanism configured: {fencing_resources}')
    return azure_fence_agent, sbd_fence_agent

def SAPHanaChecker(resources):
    i = resources
    printed=False
    logger.info(i.attrib['id'])
    #if i.attrib['id'].find('Topology') == -1:
    #    logger.info('Customer have SAP hana cluster')
    #    print('Customer have SAP hana cluster')
    cluster_type='SAPHana'
    if i.attrib['id'].find('Topology') != -1:
        issues_dict = {}
        logger.info('Customer have SAP hana cluster')
        print('Customer have SAP hana cluster')
        printed=True
        logger.info(i.attrib['id'])
        logger.info('Checking on the topology resource metadata as per our documentation')
        logger.info(i[0])
        issues_dict['topology_metadata']={}
        issues_dict['topology_operation']={}
        for j in i[0]:
            logger.info(j.attrib['name'])
            if j.attrib['name'] == 'clone-node-max' and j.attrib['value'] != "1":
                issues_dict['topology_metadata'].update({'clone-node-max' : j.attrib['value']})
            elif j.attrib['name'] == 'interleave' and j.attrib['value'] != 'true':
                issues_dict['topology_metadata'].update({'interleave' : j.attrib['value']})
        logger.info('Checking on the permittive on SAP Topology')
        logger.info(i[1].attrib['id'])
        logger.info(i[1].attrib['type'])
        for j in i[1][0]:
            if j.attrib['name'] == 'monitor' and (j.attrib['interval'] != "10" or j.attrib['timeout'] != "600"):
                    issues_dict['topology_operation'].update({'monitor' : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
            if j.attrib['name'] == 'start' and (j.attrib['interval'] != "0" or j.attrib['timeout'] != "600"):
                issues_dict['topology_operation'].update({'start' : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
            if j.attrib['name'] == 'stop' and (j.attrib['interval'] != "0" or j.attrib['timeout'] != "300"):
                issues_dict['topology_operation'].update({'stop' : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
        
        if issues_dict['topology_metadata'] or issues_dict['topology_operation']:
            logger.info(f'SAP topology has issues below {issues_dict}')
            print(f'SAP topology has issues below {issues_dict}')
            

    elif i.attrib['id'].find('SAPHana') != -1 and i.attrib['id'].find('Topology') == -1:
        issues_dict = {}
        #if not printed:
        #    logger.info('Customer have SAP hana cluster')
        #    print('Customer have SAP hana cluster')
        logger.info(i.attrib['id'])
        logger.info('Checking on the SAP resource as per our documentation')
        issues_dict['Hana_metadata']={}
        issues_dict['Hana_operation']={}
        issues_dict['Hana_instance_attributes']={}
        logger.info(i[0])
        for j in i[0]:
            logger.info(j.attrib['name'])
            if j.attrib['name'] == 'clone-node-max' and j.attrib['value'] != "1":
                issues_dict['Hana_metadata'].update({j.attrib['name'] : j.attrib['value']})
            elif j.attrib['name'] == 'interleave' and j.attrib['value'] != 'true':
                issues_dict['Hana_metadata'].update({j.attrib['name'] : j.attrib['value']})
            elif j.attrib['name'] == 'is-managed' and j.attrib['value'] != 'true':
                issues_dict['Hana_metadata'].update({j.attrib['name'] : j.attrib['value']})
            elif j.attrib['name'] == 'notify' and j.attrib['value'] != 'true':
                issues_dict['Hana_metadata'].update({j.attrib['name'] : j.attrib['value']})
            elif j.attrib['name'] == 'clone-max' and j.attrib['value'] != '2':
                issues_dict['Hana_metadata'].update({j.attrib['name'] : j.attrib['value']})                
        
        logger.info('Checking on the permittive of SAP Hana')
        logger.info(i[1].attrib['id'])
        logger.info(i[1].attrib['type'])
        for j in i[1][0]:
            if j.attrib['name'] == 'monitor' and j.attrib['role'] == 'Master' and (j.attrib['interval'] != "60" or j.attrib['timeout'] != "700"):
                    issues_dict['Hana_operation'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
            if j.attrib['name'] == 'monitor' and j.attrib['role'] == 'Slave' and (j.attrib['interval'] != "61" or j.attrib['timeout'] != "700"):
                issues_dict['Hana_operation'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
            if j.attrib['name'] == 'start' and (j.attrib['interval'] != "0" or j.attrib['timeout'] != "3600"):
                issues_dict['Hana_operation'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
            if j.attrib['name'] == 'stop' and (j.attrib['interval'] != "0" or j.attrib['timeout'] != "3600"):
                issues_dict['Hana_operation'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
            if j.attrib['name'] == 'promote' and (j.attrib['interval'] != "0" or j.attrib['timeout'] != "3600"):
                issues_dict['Hana_operation'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
        
        logger.info('Checking on the instance_attributes of SAP Hana')
        logger.info(i[1][1].attrib['id'])
        for j in i[1][1]:
            if j.attrib['name'] == 'PREFER_SITE_TAKEOVER' and j.attrib['value'] != 'true':
                issues_dict['Hana_instance_attributes'].update({j.attrib['name'] : j.attrib['value']})
            if j.attrib['name'] == 'DUPLICATE_PRIMARY_TIMEOUT' and j.attrib['value'] != '7200':
                issues_dict['Hana_instance_attributes'].update({j.attrib['name'] : j.attrib['value']})
            if j.attrib['name'] == 'SID':
                sid = j.attrib['value']
            if j.attrib['name'] == 'InstanceNumber':
                instanceNumber = j.attrib['value']
            if j.attrib['name'] == 'AUTOMATED_REGISTER':
                auto_register = j.attrib['value']
        
        logger.info('\033[93m' + f'Customer has database of name {sid} and instance number {instanceNumber}, please also note that the vaule for AUTOMATED_REGISTER is {auto_register}' + '\033[0m')
        print('\033[93m' + f'Customer has database of name {sid} and instance number {instanceNumber}, please also note that the vaule for AUTOMATED_REGISTER is {auto_register}' + '\033[0m')

        if issues_dict['Hana_metadata'] or issues_dict['Hana_operation']:
            logger.info(f'SAP Hana has issues below {issues_dict}')
            print(f'SAP Hana has issues below {issues_dict}')

def ASCSGroupChecker(resources):
    i = resources
    fs_issues={}
    logger.info(i.attrib['id'])
    logger.info('Customer have ASCS/ERS cluster')
    print('Customer have ASCS/ERS cluster')
    logger.info('Start checking on the ASCS resource group')
    for resource in i:
        if 'type' in resource.keys():
            #print(type(resource.attrib['type']))
            if resource.attrib['type'] == 'Filesystem':
                logger.info('Start checking on ASCS file system all details')
                fs_issues['ascs_fs_operation']={}
                logger.info(f'Resource name checking is {resource.attrib["id"]}')
                logger.info('Checking on instance_attributes')
                for j in resource[0]:
                    if j.attrib['name'] == 'device':
                        device=j.attrib['value']
                    elif j.attrib['name'] == 'directory':
                        mountpoint=j.attrib['value']
                    elif j.attrib['name'] == 'fstype':
                        fstype=j.attrib['value']
                logger.info('\033[93m' + f'ASCS file system is {fstype}, and the source device is {device} and mounted on {mountpoint}'+'\033[0m')
                print('\033[93m' + f'ASCS file system is {fstype}, and the source device is {device} and mounted on {mountpoint}'+'\033[0m')
                logger.info('Checking file system operation parameters:')
                for j in resource[1]:
                    if j.attrib['name'] == 'monitor' and (j.attrib['interval'].find('20') == -1 or j.attrib['timeout'].find('40') == -1 ):
                        fs_issues['ascs_fs_operation'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
                    if j.attrib['name'] == 'start' and (j.attrib['interval'] != "0" or j.attrib['timeout'].find('60') == -1):
                        fs_issues['ascs_fs_operation'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
                    if j.attrib['name'] == 'stop' and (j.attrib['interval'] != "0" or j.attrib['timeout'].find('60') == -1):
                        fs_issues['ascs_fs_operation'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
                
                if fs_issues['ascs_fs_operation']:
                    logger.info(f'ASCS file system resource has following issues {fs_issues}')
                    print(f'ASCS file system resource has following issues {fs_issues}')

            elif resource.attrib['type'] == 'anything' or resource.attrib['type'] == 'azure-lb':
                if resource.attrib['type'] == 'anything':
                    logger.info('Customer is using socat or nc for load balancer probing')
                    for j in resource[0]:
                        if j.attrib['name'] == 'binfile':
                            command = j.attrib['value']
                        if j.attrib['name'] == 'cmdline_options':
                            options = j.attrib['value']
                    logger.info('\033[93m' + f'cusotmer is using command {command} with the following options {options} for azure load balancer probing for ASCS'+'\033[0m')
                    print('\033[93m' + f'cusotmer is using command {command} with the following options {options} for azure load balancer probing for ASCS'+'\033[0m')
                    fs_issues['socat_operations']={}
                    if resource[1][0].attrib['name'] == 'monitor' and (resource[1][0].attrib['interval'].find('10') == -1 or resource[1][0].attrib['timeout'].find('20') == -1 ):
                        fs_issues['socat_operations'].update({resource[1][0].attrib['name'] : { 'interval': resource[1][0].attrib['interval'] , 'timeout' : resource[1][0].attrib['timeout'] }})
                    
                    if fs_issues['socat_operations']:
                        logger.info(f'ASCS Azure lb has the following issues {fs_issues}')
                        print(f'ASCS Azure lb has the following issues {fs_issues}')  

                else:
                    logger.info('Customer is using azure-lb')
                    print('Customer is using azure-lb for load balancer probing')
            
            elif resource.attrib['type'] == 'SAPInstance':
                logger.info('Checking on ASCS resource and start with operations')
                fs_issues['ascs_operations']={}
                for j in resource[0]:
                    if j.attrib['name'] == 'monitor' and (j.attrib['interval'] != '11' or j.attrib['timeout'] != '60'  ):
                        fs_issues['ascs_operations'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
                
                if fs_issues['ascs_operations']:
                    logger.info(f'ASCS resource has following issues on operations {fs_issues}')
                    print(f'ASCS resource has following issues on operations {fs_issues}')
                
                logger.info('Moving to check on the instance metadata information for ASCS')
                for j in resource[1]:
                    if j.attrib['name'] == 'InstanceName':
                        instanceName=j.attrib['value']
                    if j.attrib['name'] == 'START_PROFILE':
                        startProfile=j.attrib['value']
                    if j.attrib['name'] == 'AUTOMATIC_RECOVER':
                        recoverState=j.attrib['value']
                logger.info(f'ASCS instance name {instanceName} amd the start profile is located under {startProfile} and automatic recover is set to {recoverState}')
                print(f'ASCS instance name {instanceName} amd the start profile is located under {startProfile} and automatic recover is set to {recoverState}')


def ERSGroupChecker(resources):
    i = resources
    fs_issues={}
    logger.info(i.attrib['id'])
    logger.info('Customer have ASCS/ERS cluster')
    #print('Customer have ASCS/ERS cluster')
    logger.info('Start checking on the ERS resource group')
    for resource in i:
        if 'type' in resource.keys():
            #print(type(resource.attrib['type']))
            if resource.attrib['type'] == 'Filesystem':
                logger.info('Start checking on ERS file system all details')
                fs_issues['ers_fs_operations']={}
                logger.info(f'Resource name checking is {resource.attrib["id"]}')
                logger.info('Checking on instance_attributes')
                for j in resource[0]:
                    if j.attrib['name'] == 'device':
                        device=j.attrib['value']
                    elif j.attrib['name'] == 'directory':
                        mountpoint=j.attrib['value']
                    elif j.attrib['name'] == 'fstype':
                        fstype=j.attrib['value']
                logger.info('\033[93m' + f'ERS file system is {fstype}, and the source device is {device} and mounted on {mountpoint}'+'\033[0m')
                print('\033[93m' + f'ERS file system is {fstype}, and the source device is {device} and mounted on {mountpoint}'+'\033[0m')
                logger.info('Checking file system operation parameters:')
                for j in resource[1]:
                    if j.attrib['name'] == 'monitor' and (j.attrib['interval'].find('20') == -1 or j.attrib['timeout'].find('40') == -1 ):
                        fs_issues['ers_fs_operations'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
                    if j.attrib['name'] == 'start' and (j.attrib['interval'] != "0" or j.attrib['timeout'].find('60') == -1):
                        fs_issues['ers_fs_operations'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
                    if j.attrib['name'] == 'stop' and (j.attrib['interval'] != "0" or j.attrib['timeout'].find('60') == -1):
                        fs_issues['ers_fs_operations'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
                
                if fs_issues['ers_fs_operations']:
                    logger.info(f'ERS file system resource has following issues {fs_issues}')
                    print(f'ERS file system resource has following issues {fs_issues}')

            elif resource.attrib['type'] == 'anything' or resource.attrib['type'] == 'azure-lb':
                if resource.attrib['type'] == 'anything':
                    logger.info('Customer is using socat or nc for load balancer probing')
                    for j in resource[0]:
                        if j.attrib['name'] == 'binfile':
                            command = j.attrib['value']
                        if j.attrib['name'] == 'cmdline_options':
                            options = j.attrib['value']
                    logger.info('\033[93m' + f'cusotmer is using command {command} with the following options {options} for azure load balancer probing for ERS'+'\033[0m')
                    print('\033[93m' + f'cusotmer is using command {command} with the following options {options} for azure load balancer probing for ERS'+'\033[0m')
                    fs_issues['socat_operations']={}
                    if resource[1][0].attrib['name'] == 'monitor' and (resource[1][0].attrib['interval'].find('10') == -1 or resource[1][0].attrib['timeout'].find('20') == -1 ):
                        fs_issues['socat_operations'].update({resource[1][0].attrib['name'] : { 'interval': resource[1][0].attrib['interval'] , 'timeout' : resource[1][0].attrib['timeout'] }})
                    
                    if fs_issues['socat_operations']:
                        logger.info(f'ERS Azure lb has the following issues {fs_issues}')
                        print(f'ERS Azure lb has the following issues {fs_issues}')  

                else:
                    logger.info('Customer is using azure-lb')
                    print('Customer is using azure-lb for load balancer probing')
            
            elif resource.attrib['type'] == 'SAPInstance':
                logger.info('Checking on ERS resource and start with operations')
                fs_issues['ers_operations']={}
                for j in resource[0]:
                    if j.attrib['name'] == 'monitor' and (j.attrib['interval'] != '11' or j.attrib['timeout'] != '60'  ):
                        fs_issues['ers_operations'].update({j.attrib['name'] : { 'interval': j.attrib['interval'] , 'timeout' : j.attrib['timeout'] }})
                
                if fs_issues['ers_operations']:
                    logger.info(f'ERS resource has following issues on operations {fs_issues}')
                    print(f'ERS resource has following issues on operations {fs_issues}')
                
                logger.info('Moving to check on the instance metadata information for ERS')
                for j in resource[1]:
                    if j.attrib['name'] == 'InstanceName':
                        instanceName=j.attrib['value']
                    if j.attrib['name'] == 'START_PROFILE':
                        startProfile=j.attrib['value']
                    if j.attrib['name'] == 'AUTOMATIC_RECOVER':
                        recoverState=j.attrib['value']
                    if j.attrib['name'] == 'IS_ERS':
                        isERS=j.attrib['value']
                logger.info(f'ERS instance name {instanceName} amd the start profile is located under {startProfile} and automatic recover is set to {recoverState} and has IS_ERS set to {isERS}')
                print(f'ERS instance name {instanceName} amd the start profile is located under {startProfile} and automatic recover is set to {recoverState} and has IS_ERS set to {isERS}')


def getClusterType(root_xml):
    cluster_resources = root_xml[2]
    logger.info(cluster_resources)
    cluster_type=""
    #issues_dict = {}
    

    for i in cluster_resources:
        if i.attrib['id'].find('SAPHana') != -1:
            SAPHanaChecker(i)
        
        elif i.attrib['id'].find('ASCS') != -1 or i.attrib['id'].find('ERS') != -1:
            logger.info(i.attrib['id'])
            cluster_type='ASCSERS'
            if i.attrib['id'].find('ASCS') != -1:
                ASCSGroupChecker(i)
            elif i.attrib['id'].find('ERS') != -1:
                ERSGroupChecker(i)
                                                              

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
    
    #sr_num = collect_sr()
    logger.info(path_to_scc)
    #log_case_scc(sr_num, path_to_scc)
    if checkFileExistance(path_to_scc):
        version_id = osVersion(path_to_scc)
        root_xml = readingCib(path_to_scc)
        azure_fence_agent, sbd_fence_agent = propertyChecker(root_xml)
        getClusterType(root_xml)
        totemChecker(path_to_scc)
        quorumChecker(path_to_scc)
        rpmChecker(path_to_scc, version_id, azure_fence_agent, sbd_fence_agent)
        



    
    


