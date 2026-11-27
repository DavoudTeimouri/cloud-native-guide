# Longhorn

## Symptoms
- Volume stuck in Pending/Attaching
- Replica failed or stuck
- Volume expansion failing
- Snapshot/backup failing
- Longhorn manager not running

## Possible causes
- Longhorn manager/engine/replica not running
- Node lacks available disk for replica
- Volume replica count unsatisfiable
- StorageClass not matching Longhorn
- Backup target (NFS/S3) unreachable

## Diagnostic commands
```bash
# Longhorn
kubectl get pods -n longhorn-system
kubectl get volumes.longhorn.io
kubectl get replicas.longhorn.io
kubectl get engines.longhorn.io
kubectl describe volume.longhorn.io <volume>

# StorageClass
kubectl get storageclass longhorn

# Backup target
kubectl get settings.longhorn.io backup-target
```

## Expected output
- longhorn-manager: Running
- volume: Ready/Healthy
- replica: Running/Healthy
- engine: Running/Healthy

## Investigation procedure
1. Check Longhorn system pods running
2. Check volume/replica/engine status
3. Check StorageClass provisioner is longhorn.io
4. Check backup target accessibility
5. Check node disk availability for replicas

## Resolution
- Restart Longhorn manager/engine/replica
- Add node with available disk; adjust replica count
- Fix StorageClass or update volume
- Fix backup target connectivity

## Verification
- Longhorn system Running; volume Ready/Healthy; replica Running/Healthy; engine Running/Healthy

## Prevention
- Monitor Longhorn system health; alert on crash
- Monitor volume health; alert on degraded
- Monitor replica disk space; alert at threshold

## Related
- [07 · Software-Defined Storage (7.5 Other SDS Solutions)](../07-software-defined-storage/7.5-other-sds-solutions.md)
