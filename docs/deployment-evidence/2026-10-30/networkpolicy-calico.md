# NetworkPolicy enforcement on kind + Calico v3.28.2 (2026-10-30T14:49Z)

Each line opens a TCP connection from inside a running pod.

```
reachable   frontend -> api:8000          (allowed)
BLOCKED     frontend -> postgres:5432     (not allowed)
BLOCKED     frontend -> redis:6379        (not allowed)
BLOCKED     frontend -> keycloak:8080     (not allowed)
reachable   api -> postgres:5432          (allowed)
reachable   api -> redis:6379             (allowed)
reachable   api -> keycloak:8080          (allowed)
reachable   worker -> postgres:5432       (allowed)
reachable   worker -> redis:6379          (allowed)
BLOCKED     worker -> keycloak:8080       (not allowed)
BLOCKED     worker -> api:8000            (not allowed)
```

## Reliability of allowed connections (40 fresh connections, API pod to Keycloak)
```
fresh connections: 40, failed 0 slower than 1s 0 max 0.01
```

Same test on kindnet (kind's default CNI), earlier the same day: 7 of 40 failed and 17 took over a second.
