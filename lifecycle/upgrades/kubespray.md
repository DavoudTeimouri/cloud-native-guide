# Kubespray Upgrade Procedure

## A. Purpose and scope

Document the Kubespray upgrade procedure. kubespray-deployment.md references this file for diffing group-vars across releases. Covers inventory diffing, Ansible version compatibility, control-plane upgrade sequencing, and etcd upgrade considerations.

## B. Prerequisites

- Pin the Kubespray release in `kubespray/VERSION`; never track `master`
- Keep inventory and group vars in Git; cluster must be reproducible from repo
- Mirror every image the deploy uses, verified by pull test in offline environment
- Record Ansible and Python versions in `automation/ansible/requirements.txt`
- Run `--check --diff` on control-plane before any real run

## C. Inventory diffing procedure

Kubespray variables change between releases. Never reuse a group-vars file across a Kubespray release without diffing it against the new release's `inventory/sample`.

```bash
# Diff existing inventory against new release sample
diff -ru inventory/<cluster>/group_vars/ <new-kubespray>/inventory/sample/group_vars/

# Review all differences before applying
# Update group_vars to match new release expectations
```

## D. Ansible version compatibility

Kubespray release-2.32 requires Ansible >=2.19.0, <2.20.0 (2.19.x) and Python 3.11-3.13.

```bash
# Verify Ansible version
ansible --version

# Verify Python version
python3 --version

# Check requirements.txt
cat automation/ansible/requirements.txt
```

**Never mix Ansible versions across Kubespray releases.** Each release gets its own Python virtualenv.

## E. Control-plane upgrade sequence

**One control-plane node at a time — preserve quorum:**

1. On one control-plane node, apply updated inventory and group_vars
2. Run Kubespray deploy: `ansible-playbook -i inventory/<cluster>/hosts.ini cluster.yml`
3. Verify node is healthy: `kubectl get nodes` and `kubectl get --raw='/readyz?verbose'`
4. Repeat for the next control-plane node

**Do not restart all control-plane nodes simultaneously** — this removes API server quorum and makes the cluster unreachable.

## F. etcd upgrade considerations

etcd is deployed as static pods managed by kubelet. Upgrade etcd by:

1. Update `etcd_version` in group_vars
2. Run Kubespray deploy for control-plane nodes one at a time
3. Verify etcd health: `etcdctl --endpoints=https://127.0.0.1:2379 endpoint health --cluster`
4. Verify quorum: `kubectl get --raw='/readyz?verbose'`

## G. Rollback

Kubespray does not provide automated rollback. Before upgrading:

1. Backup etcd: `etcdctl snapshot save /tmp/etcd-backup-<date>.db`
2. Backup inventory: `git commit inventory/<cluster>/`
3. Test upgrade on a single control-plane node first

If upgrade fails, restore etcd from snapshot and revert inventory changes.

## H. Cross-references

- `kubespray/kubespray-deployment.md` — Kubespray deployment
- `ADR-0026` — Kubespray multi-version support (five parallel releases)
- `compatibility/version-matrix.md` — Version pins and compatibility
