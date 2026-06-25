# Runbook: Pod CrashLoopBackOff caused by OOMKilled

## Summary
A pod repeatedly restarts and enters `CrashLoopBackOff`. The container is being
terminated by the kernel OOM killer (`OOMKilled`, exit code 137) because it
exceeds its configured memory limit.

## Symptoms
- Pod status shows `CrashLoopBackOff` with rising `restart_count`.
- Container last state `Terminated` with reason `OOMKilled` (exit code 137).
- Memory utilization at or near 100% of the limit just before restart.
- Garbage collection pauses increasing; allocation pressure warnings in logs.

## Likely Causes
- Memory limit set too low for real traffic.
- Memory leak or unbounded in-memory cache / buffer growth.
- A traffic spike increasing concurrent request memory footprint.

## Diagnosis
- Inspect the pod and its last termination reason:
  `kubectl describe pod <pod> -n <namespace>`
- Check live and historical memory usage:
  `kubectl top pod <pod> -n <namespace>`
- Review recent restarts:
  `kubectl get pod <pod> -n <namespace> -o jsonpath='{.status.containerStatuses[0].restartCount}'`

## Remediation
1. Provide immediate headroom by raising the memory limit:
   `kubectl set resources deployment/<name> -n <namespace> --limits=memory=1Gi --requests=memory=768Mi`
2. Scale out to spread load while you investigate:
   `kubectl scale deployment/<name> -n <namespace> --replicas=5`
3. If a leak is suspected, roll back to the last known-good image:
   `kubectl rollout undo deployment/<name> -n <namespace>`
4. Verify recovery:
   `kubectl rollout status deployment/<name> -n <namespace>`

## Prevention
- Add memory-based Horizontal Pod Autoscaling.
- Set alerts at 85% of the memory limit.
- Add heap profiling in staging and load test before release.
