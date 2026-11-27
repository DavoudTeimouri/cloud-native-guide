# Offline Upgrade Test



## A. Purpose and scope



End-to-end test procedure for offline upgrade validation in air-gapped environments. Verifies that Kubernetes clusters can be upgraded without internet access, using only pre-mirrored artifacts from internal registries and mirrors.



Cross-references `` `offline-artifacts/artifact-matrix.md` ``, `` `offline-artifacts/offline-upgrade-procedure.md` ``, `` `offline-artifacts/offline-artifact-architecture.md` ``, `` `security/image-provenance.md` ``, and `` `lifecycle/upgrades/kubernetes.md` ``.



## B. Test prerequisites



- Air-gapped environment with internal artifact mirror (Harbor/Nexus) populated per `offline-artifacts/artifact-matrix.md`

- Verified offline artifacts: images, Helm charts, OS packages, binaries — all signed and checksummed per `offline-artifacts/signature-verification.md`

- Kubespray release tagged and mirrored to internal Git

- `kubectl` configured against the target cluster

- etcd snapshot verified per `kubernetes/control-plane/etcd-restore.md`



## C. Test steps



### Test 1: Artifact availability validation



1. Confirm all required artifacts are present in the internal mirror:

   ```bash

   # Validate Kubernetes components

   crictl pull harbor.internal/platform/kubernetes/kube-apiserver:v1.36.5



   # Validate Kubespray roles

   ansible-galaxy collection list | grep kubernetes.core



   # Validate CNI plugin

   ls /opt/cni/bin/cilium *

   ```

2. Verify artifact signatures and SBOMs per `offline-artifacts/signature-verification.md`:

   ```bash

   # Cosign image verification

   cosign verify --key cosign.pub registry.internal/:<tag>



   # SBOM verification

   cosign verify sbom --key cosign.pub --sbom sbom.json registry.internal/:<tag>

   ```

3. Confirm OS package checksums:

   ```bash

   sha256sum -c <checksum-file>

   ```



### Test 2: Offline upgrade playbook execution



1. Run the Kubespray offline upgrade playbook:

   ```bash

   # From the mirrored Kubespray repository

   ansible-playbook -i inventory/<cluster> upgrade.yml \

     --extra-vars "kubernetes_version=v1.36.5 kubespray_version=v2.27.0"

   ```

2. Monitor upgrade phases per `offline-artifacts/offline-upgrade-procedure.md`:

   - Phase 1: Inventory new artifacts ✓

   - Phase 2: Validate artifacts ✓

   - Phase 3: Upgrade etcd (rolling, one member at a time)

   - Phase 4: Upgrade control plane (rolling kube-apiserver/scheduler/controller-manager)

   - Phase 5: Upgrade workers (drain, upgrade kubelet/container runtime, uncordon)

   - Phase 6: Upgrade CNI (rolling Cilium upgrade)

   - Phase 7: Upgrade addons (ingress, metrics-server, etc.)



### Test 3: Post-upgrade validation



1. Verify cluster nodes are Ready:

   ```bash

   kubectl get nodes -o wide

   ```

2. Verify API server health:

   ```bash

   kubectl get componentstatuses

   ```

3. Verify workloads are scheduling:

   ```bash

   kubectl get pods -A -o wide

   ```

4. Verify CNI connectivity:

   ```bash

   cilium status

   ```

5. Verify ingress functionality:

   ```bash

   kubectl get ingress -A

   ```



### Test 4: Rollback validation (failure scenario)



1. etcd rollback:

   ```bash

   # Restore from verified snapshot

   kubectl patch etcd <name> -p '{"spec":{"backupPlanName":"<snapshot-name>"}}'

   ```

2. Control plane rollback:

   ```bash

   # Revert to previous Kubespray version

   ansible-playbook -i inventory/<cluster> upgrade.yml \

     --extra-vars "kubernetes_version=v1.36.4 kubespray_version=v2.26.0"

   ```

3. Worker rollback:

   ```bash

   # Revert kubelet and container runtime to previous version

   ```



## D. Test success criteria



- [ ] All required artifacts are present and verified in the internal mirror

- [ ] All artifact signatures and SBOMs verify successfully

- [ ] Upgrade playbook executes without errors

- [ ] All cluster nodes reach Ready state post-upgrade

- [ ] API server and component health checks pass

- [ ] CNI connectivity is functional

- [ ] Ingress/load balancing is operational

- [ ] Rollback procedures verified (documented, not necessarily executed)

- [ ] Zero downtime or documented minimal downtime per phase



## E. Cross-references



- `` `offline-artifacts/artifact-matrix.md` `` — Artifact matrix with versions and validation commands

- `` `offline-artifacts/offline-upgrade-procedure.md` `` — Phase-by-phase upgrade procedure

- `` `offline-artifacts/offline-artifact-architecture.md` `` — Architecture and mirror configuration

- `` `security/image-provenance.md` `` — Image signing and Cosign verification

- `` `lifecycle/upgrades/kubernetes.md` `` — Kubernetes upgrade procedure reference
