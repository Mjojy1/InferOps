# Runbook: Elevated 5xx Error Rate

## Summary
A service is returning an elevated rate of 5xx responses. This runbook helps
distinguish a bad deploy from a failing dependency and restore the error budget.

## Symptoms
- Error rate above the SLO threshold (e.g. > 2%).
- Spike begins shortly after a deploy, config change, or dependency incident.
- Mixed `500`/`503` responses, sometimes with upstream timeouts.

## Likely Causes
- A recent bad rollout (regression or misconfiguration).
- A failing or throttled downstream dependency.
- Resource exhaustion (CPU/memory) causing dropped requests.

## Diagnosis
- Correlate the error spike with the deploy timeline:
  `kubectl rollout history deployment/<name> -n <namespace>`
- Inspect recent error logs:
  `kubectl logs deployment/<name> -n <namespace> --since=15m | grep -E "5[0-9]{2}|ERROR"`
- Check dependency health and saturation in dashboards.

## Remediation
1. If the spike followed a deploy, roll back immediately:
   `kubectl rollout undo deployment/<name> -n <namespace>`
2. If a dependency is failing, enable the circuit breaker / serve degraded mode.
3. Shed load with rate limiting until the system stabilizes.
4. Verify recovery:
   `kubectl rollout status deployment/<name> -n <namespace>`

## Prevention
- Use progressive delivery (canary / blue-green) with automated rollback.
- Add SLO burn-rate alerts.
- Make dependencies fail gracefully with timeouts and fallbacks.
