# Runbook: P99 Latency Spike from Upstream Dependency

## Summary
A service shows a sharp increase in tail (p99) latency while p50 stays low. The
extra latency usually comes from a slow or saturated downstream dependency
(database, cache, or another microservice) rather than the service itself.

## Symptoms
- p99 latency rises sharply while p50 remains near baseline.
- Logs show `upstream timeout` or `connection pool exhausted`.
- Downstream dependency reports slow queries or elevated saturation.

## Likely Causes
- Connection pool to a database or service is exhausted.
- A slow query or missing index on the downstream datastore.
- Retry storms multiplying load on a degraded dependency.

## Diagnosis
- Identify the slow hop in distributed traces (look for the longest span).
- Check downstream saturation and pool usage:
  `kubectl top pod <downstream-pod> -n <namespace>`
- Inspect slow queries on the datastore (e.g. `pg_stat_activity`).

## Remediation
1. Increase the connection pool / client timeout budget for the dependency.
2. Add or tune a circuit breaker so retries do not amplify load.
3. Scale the downstream dependency:
   `kubectl scale deployment/<downstream> -n <namespace> --replicas=6`
4. Add a short-TTL cache for hot read paths to shed downstream traffic.

## Prevention
- Set explicit timeouts and bounded retries on every network call.
- Add SLO-based alerts on p99, not just averages.
- Capacity-plan downstream dependencies against peak fan-out.
