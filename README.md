# Cluster checker script
Script for checking cluster configuration on SUSE cluster
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