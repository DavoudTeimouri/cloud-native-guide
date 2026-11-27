# 02 · Components

Preparation and configuration of every infrastructure component before deploying the Cloud-Native stack. This section is about readying the hardware, OS, and per-role node configuration — it does not deploy Kubernetes itself (see [06 · Kubernetes](../06-kubernetes-infrastructure/)).

## Purpose
Document how to prepare each type of infrastructure node (OS, physical/virtual, storage, load balancer, registry, GitLab, operation servers) so they are ready to receive the Cloud-Native stack.

## Subsections

| Subsection | Covers |
|---|---|
| [2.1 Operating Systems](2.1-operating-systems.md) | Oracle Linux, RHEL, Rocky, Alma, Ubuntu, Debian, SLES, Windows Server; support status, install, offline, hardening, network, DNS/NTP, storage, firewall, packages, kernel, updates, automation |
| [2.2 Physical vs Virtual Machines](2.2-physical-vs-vm.md) | Bare-metal vs VM vs hybrid; advantages, disadvantages, operational implications, performance, failure-domain implications |
| [2.3 Physical Infrastructure Preparation](2.3-physical-infra-prep.md) | Server hardware, CPU/memory, BIOS/UEFI, firmware, RAID/HBA, disk controller, NIC, multipathing, BMC/remote mgmt, compatibility, Secure Boot, NUMA, power, monitoring |
| [2.4 Virtualization Platform Preparation](2.4-virtualization-prep.md) | VMware vSphere/ESXi, KVM/Proxmox VE; install, networking, distributed switching, storage integration, HA, VM sizing, reservations, anti-affinity, passthrough, backup |
| [2.5 OS Preparation by Role](2.5-os-prep-by-role.md) | Role-specific procedures: general Linux, K8s control-plane, K8s worker, storage, load balancer, registry manager, GitLab, automation, monitoring nodes |
| [2.6 Operation & Management Servers](2.6-operation-mgmt-servers.md) | Mgmt environment design; pair of Linux mgmt/automation servers + Windows mgmt server; Ansible, Kubespray, SSH, PowerShell, Git, cert/secret mgmt, admin access, audit logging |
| [2.7 Kubernetes Nodes](2.7-kubernetes-nodes.md) | Control-plane, worker, infrastructure worker, GPU worker, specialized app worker node prep |
| [2.8 Ceph & Storage Nodes](2.8-ceph-storage-nodes.md) | Ceph MON/MGR/OSD/MDS/RGW prep; disk, network, CPU, memory, failure-domain considerations |
| [2.9 Load Balancer Nodes](2.9-lb-nodes.md) | LB OS prep, network config, VIP support, HA, operational hardening |
| [2.10 Repository & Registry Manager Servers](2.10-repo-registry-servers.md) | Nexus, Harbor, and other repo/registry infra; native and container-based deployment requirements |
| [2.11 GitLab Server](2.11-gitlab-server.md) | GitLab infra requirements, OS prep, storage, networking, security, backup, dependencies |
| [2.12 Other Infrastructure Components](2.12-other-infra.md) | DNS, NTP, PKI/CA, LDAP/AD, Vault/secret managers, SMTP, backup infra, security scanning, vuln management |

## Cross-references
- Components consume the [shared network matrix](../shared/network-matrix/) for port/firewall requirements.
- See [03 · Repository and Registry Management](../03-repository-registry/) for the software-distribution architecture these components consume.
- See [05 · Load Balancers](../05-load-balancers/) for LB node preparation detail.
