# Runbook: High CPU Utilization and CPU Throttling

## Summary
A service is saturating its CPU allocation. Kubernetes is throttling the
container against its CPU limit, which inflates latency and queue depth.

## Symptoms
- CPU utilization sustained above 85-90%.
- Log lines reporting `cpu throttling` (e.g. `320ms per 1s period`).
- Rising p99 latency that correlates with CPU saturation.

## Likely Causes
- CPU limit set too low for current request volume.
- An inefficient hot code path or N+1 calls.
- A poison request / retry storm amplifying work.

## Diagnosis
- Confirm throttling and usage:
  `kubectl top pod <pod> -n <namespace>`
- Inspect throttled periods (cgroup):
  `kubectl exec <pod> -n <namespace> -- cat /sys/fs/cgroup/cpu.stat`
- Correlate with request rate in your dashboard.

## Remediation
1. Raise the CPU limit to remove throttling:
   `kubectl set resources deployment/<name> -n <namespace> --limits=cpu=2 --requests=cpu=1`
2. Scale horizontally to reduce per-pod load:
   `kubectl scale deployment/<name> -n <namespace> --replicas=6`
3. Enable autoscaling on CPU:
   `kubectl autoscale deployment/<name> -n <namespace> --cpu-percent=70 --min=3 --max=10`

## Prevention
- Load test for CPU before launch.
- Keep CPU requests realistic so the scheduler bin-packs correctly.
- Profile and optimize hot paths flagged in tracing.
