# Rancher cluster upgrade procedure

[Previous step](../../kubespray/kubespray-deployment.md) | [Next step](../../network-matrix/external-load-balancer.md)

## A. Pre-upgrade validation

- Confirm the current Rancher version and embedded Kubernetes version (RKE2/K3s).
- Review the [Rancher upgrade guide](https://rancher.com/docs/rancher/v2.8/en/upgrade/) for breaking changes and deprecations.
- Verify the error budget: if the current SLO consumption is above 50% with less than 30 days remaining, defer the upgrade.
- Take a etcd snapshot of the management cluster.
- Ensure a full backup of the GitOps repositories (Fleet bundles, Argo CD applications).
- Validate that all managed clusters are in `active` state and healthy.
- Check that no pending upgrades or failed rollouts exist in the Fleet baseline.

## B. RKE2/K3s version selection

- Choose the target Kubernetes version compatible with the Rancher release being upgraded to (Rancher v2.8 → K3s v1.27+ / RKE2 v1.27+).
- Confirm that the node OS baseline (Ubuntu 22.04 / RHEL 9) supports the target K8s version.
- Record the desired K8s version in `inventory/hosts-mgmt.ini` under the `[mgmt]` section:
  ```ini
  [mgmt]
  mgmt-01 ansible_host=10.0.0.1
  mgmt-02 ansible_host=10.0.0.2
  mgmt-03 ansible_host=10.0.0.3
  kubernetes_version=v1.27.3
  ```
- Run `kubespary/cluster-upgrade-prep.sh` (if available) to pre-stage the new K8s binaries on all nodes.
- Verify that the RKE2/K3s agent version in Rancher matches the target K8s version; update the agent manifest if needed.

## C. Control plane upgrade

- Drain one control‑plane node (`kubectl drain <node> --ignore-daemonsets --delete-emptydir`).
- Upgrade K8s on the control‑plane node via Kubespray rolling upgrade:
  ```bash
  ansible-playbook -i inventory/hosts-mgmt.ini kubespray/roles/kubernetes.yml --tags=kube-apiserver
  ```
- Wait for the node to re‑join and become `Ready`.
- Repeat for each control‑plane node (3 total), draining one at a time and respecting the 5‑minute cooldown between nodes.
- After the last control‑plane node is upgraded, verify the cluster version:
  ```bash
  kubectl version --client=false | grep ServerVersion
  ```

## D. Worker node upgrade

- For each worker node group:
  1. Drain the node.
  2. Upgrade the K8s runtime and binaries using the Kubespray inventory version set in step B.
  3. Verify the node rejoins and becomes Ready.
  4. Run the Fleet reconciliation to re‑sync node metadata:
     ```bash
     fleetctl check node <node-name>
     ```
- If using node pools managed by the `node-pool-management.md` procedure, follow that workflow instead of manual drain/upgrade.
- After all workers in a group are upgraded, confirm the cluster-wide K8s version matches the target.

## E. Post‑upgrade verification

- Run the health check endpoint:
  ```bash
  curl -k https://rancher.internal/v3/health
  ```
- Verify Rancher UI loads and shows the upgraded K8s version under **Cluster Management → System**.
- Confirm all managed clusters are still registered and their nodes report the correct version:
  ```bash
  curl -sk -u "$RANCHER_TOKEN:$RANCHER_TOKEN" \
    https://rancher.internal/v3/clusters | jq '.data[] | {name, state, nodes}'
  ```
- Execute the Fleet sync check:
  ```bash
  fleetctl check --targets all
  ```
- Review the etcd metrics for any spike in latency or failed proposals immediately after the upgrade.
- If using monitoring, confirm that SLO error‑budget consumption has not spiked (e.g., latency p99 within target).

## F. Rollback procedures

- **Rollback window**: Within 2 hours of upgrade completion, before the error budget is significantly consumed.
- **Control plane**: To rollback a single control‑plane node, re‑apply the previous Kubespray tags (`kubespray/roles/kubernetes.yml --tags=kube-apiserver`) with the prior `kubernetes_version`. Drain the node, apply the older version, and uncordon.
- **Worker nodes**: Re‑run the Kubespray playbook with the previous `kubernetes_version` on the affected worker(s). Drain, downgrade, uncordon.
- **Rancher Helm chart**: If the Rancher upgrade itself caused issues, `helm rollback -n cattle-system rancher <revision>` can revert the Rancher Helm release.
- After any rollback, re‑verify the health check, cluster state, and SLO metrics. Document the rollback in the incident tracker and schedule a post‑mortem to identify the root cause.

[Previous step](../../kubespray/kubespray-deployment.md) | [Next step](../../network-matrix/external-load-balancer.md)
