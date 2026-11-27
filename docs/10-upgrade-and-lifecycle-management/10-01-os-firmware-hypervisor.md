# OS, Firmware, Hypervisor

## Purpose and scope
OS patches, firmware, hypervisor upgrades; compatibility, backup, rollback.

## Steps
1. Check compatibility matrix for supported versions
2. Backup node/VM
3. Schedule maintenance window
4. Apply patch/firmware/hypervisor upgrade
5. Reboot if required
6. Verify node Ready; workloads rescheduled

## Implementation
```bash
# OS patch (Oracle Linux/Ubuntu)
dnf update -y <package>   # OL/RHEL/Rocky/Alma
apt update && apt upgrade -y <package>  # Ubuntu

# Firmware via BMC/vendor tool
# Hypervisor upgrade via vCenter/Proxmox/vSphere client

# Verify node
kubectl get nodes <node>
kubectl describe node <node>
```

## Validation
- Node Ready after reboot
- Pods rescheduled correctly
- Services healthy

## Related
- [Operating Systems (2.1 Operating Systems)](../02-components/2.1-operating-systems.md)
- [Operating Systems (2.3 Physical Infrastructure Preparation)](../02-components/2.3-physical-infra-prep.md)
- [Operating Systems (2.4 Virtualization Platform Preparation)](../02-components/2.4-virtualization-prep.md)
