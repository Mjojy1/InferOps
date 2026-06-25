# Runbook: Disk Pressure / No Space Left on Device

## Summary
A node or persistent volume is running out of disk. Kubernetes taints the node
with `disk-pressure` and may evict pods. Writers fail with
`no space left on device`.

## Symptoms
- Disk utilization above 90% on a volume or node.
- Errors like `no space left on device` or failed checkpoint writes.
- Node taint `node.kubernetes.io/disk-pressure` and pod evictions.

## Likely Causes
- Unrotated logs or growing temp files.
- A backlog/queue persisting faster than it drains.
- Undersized PersistentVolumeClaim for current retention.

## Diagnosis
- Check usage inside the pod:
  `kubectl exec <pod> -n <namespace> -- df -h`
- Find the largest directories:
  `kubectl exec <pod> -n <namespace> -- du -xh / | sort -rh | head -20`
- Check node conditions:
  `kubectl describe node <node>`

## Remediation
1. Reclaim space immediately (rotate/compress logs, clear temp):
   `kubectl exec <pod> -n <namespace> -- sh -c 'find /var/log -type f -name "*.log" -mtime +1 -delete'`
2. Expand the PersistentVolumeClaim (if the StorageClass allows expansion):
   `kubectl patch pvc <pvc> -n <namespace> -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'`
3. Drain the backlog by scaling consumers:
   `kubectl scale deployment/<consumer> -n <namespace> --replicas=4`

## Prevention
- Alert at 80% disk usage with projected time-to-full.
- Enforce log rotation and retention limits.
- Right-size PVCs and enable volume expansion.
