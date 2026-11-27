# Upgrades Troubleshooting

## Symptoms

- Control-plane upgrade fails mid-way
- Worker nodes not joining after upgrade
- Kubespray playbook fails on upgrade task
- Pods evicted during upgrade
- Version mismatch between control-plane and workers

## Likely causes

- Kubespray version incompatible with target Kubernetes version
- Control-plane upgraded before etcd
- Worker nodes drained but not uncordoned
- Image not available for new version
- etcd snapshot not taken before upgrade

## Diagnostic commands

```bash
# Check version consistency
kubectl get nodes -o wide | grep -E "VERSION|STATUS"
kubectl version --short

# Check Kubespray version
cat kubespray/VERSION

# Check playbook run status
# Review ansible-playbook output log

# Check node conditions
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, conditions: .status.conditions}'

# Check etcd health
etcdctl --endpoints=https://127.0.0.1:2379 endpoint health --cluster
```

## Expected healthy state

- All nodes: Ready, same or compatible version
- etcd: healthy quorum
- Kubespray version matches deployment (release-2.32)
- No nodes in NotReady state after upgrade

## Remediation

- Match Kubespray version to target Kubernetes version
- Upgrade control-plane nodes one at a time
- Upgrade etcd before API server
- Uncordon worker nodes after upgrade completes
- Take etcd snapshot before any upgrade

## Risks

- Upgrading all control-plane nodes simultaneously removes quorum
- Skipping etcd upgrade can cause version incompatibility
- Not taking etcd snapshot means no rollback path

## Verification

```bash
kubectl get nodes
kubectl version --short
etcdctl --endpoints=https://127.0.0.1:2379 endpoint health --cluster
cat kubespray/VERSION```
