# Sleep & Wake Lifecycle Reference

This reference covers configuring, verifying, and troubleshooting Koyeb's dual-tier sleep system (Light Sleep and Deep Sleep), idle timeout resets, wake latency benchmarking, and cost considerations.

---

## 1. Dual-Tier Sleep Architecture

Koyeb offers two progressive tiers of scale-to-zero sleep:

| Tier | Mechanism | Resume Behavior | Typical Use Case |
| :--- | :--- | :--- | :--- |
| **Light Sleep** | Snapshot-based resumption. | Fast resume; official documentation describes approximately 200ms CPU startup, not a per-request guarantee. | Eligible low-traffic services where fast wakeup matters. |
| **Deep Sleep** | Cold startup of a new runtime. | Official documentation describes typical 1–5 second cold starts; application initialization can add latency. | Eligible infrequently accessed services where cold starts are acceptable. |

### Configuration Flags
Idle timeouts are configured independently using `--light-sleep-delay` and `--deep-sleep-delay`:
```bash
# Example: 5-minute Light Sleep, Deep Sleep disabled (0 disables that specific tier)
python3 scripts/koyeb_env.py -- services update example-app/example-service \
  --light-sleep-delay 5m \
  --deep-sleep-delay 0 \
  --min-scale 0 \
  --max-scale 1 \
  --skip-build \
  --wait
```
*Note*: `5m` light and `0` deep sleep is an illustrative example, not a universal preference or platform default. Always follow the explicit task or project runbook.

---

## 2. Prerequisites & Plan Eligibility

Sleep features are subject to strict platform prerequisites:
1. **Minimum Scale Zero (`--min-scale 0`)**: Sleep can **never** trigger if `--min-scale` is $\ge 1$.
2. **Always-On Scaling & CLI Flag Refusal**: When configuring a service for always-on operation (`--min-scale 1`), **do not pass sleep delay flags** (`--light-sleep-delay` or `--deep-sleep-delay`, even set to `0`). The official Koyeb CLI strictly rejects sleep flags when `--min-scale` is $\ge 1$. Omit them entirely:
   ```bash
   python3 scripts/koyeb_env.py -- services update example-app/example-service \
     --min-scale 1 --max-scale 1 --skip-build --wait
   ```
3. **Instance Type & Plan Eligibility**: Sleep support depends on current Koyeb plan tiers and instance families (standard microVMs vs dedicated GPUs/bare-metal). Do not make unconditional assertions that sleep is supported for every plan, GPU type, or legacy tier. Consult current official Koyeb documentation for eligible instance types.
4. **Disabling Individual Tiers**: Passing `0` to a delay flag disables that specific tier (e.g. `--deep-sleep-delay 0` keeps the service in Light Sleep indefinitely rather than transitioning to Deep Sleep). This is only valid when `--min-scale 0`.
5. **Live Targets Nuance**: Read the actual deployment definition when configuration is absent from the service response. An existing `min=0` configuration with empty targets may still be running; `min=0` alone is not proof of sleep. User tasks and project runbooks define policy, not a universal sleep default in this skill.

---

## 3. Idle Resets & The "Polling Trap"

A frequent failure mode for automated agents is attempting to verify sleep state by repeatedly issuing HTTP requests to the service URL:

> **CRITICAL RULE**: Inbound HTTP data requests wake the service and reset the idle timer immediately. Never continuously poll the public HTTP endpoint to test if a service has fallen asleep. Doing so ensures the service will **never** enter sleep.

### Causes of Idle Timer Resets
- Active HTTP or WebSocket connections.
- External synthetic uptime monitors (e.g., Datadog, Pingdom, Uptime Kuma) pinging health endpoints.
- Web crawlers or search engine indexers hitting public routes.
- Ongoing deployment or scale-up events.

---

## 4. Control-Plane Verification (Safe Queries)

Control-plane API queries via the Koyeb CLI do **not** route data traffic to instances and do **not** wake sleeping workloads.

```bash
# Safe: inspects control plane state without resetting idle timers
python3 scripts/koyeb_env.py -- services describe example-app/example-service -o json

# Safe: inspects instance lifecycle status
python3 scripts/koyeb_env.py -- instances list --app example-app --service example-app/example-service -o json
```

### Scale-to-Zero Configuration vs. Active Sleep
- Having `--min-scale 0` configured is **not proof** that the service is currently asleep.
- Confirm the sleep mode through explicit platform sleep/wake events, correlated with deployment and instance state. Do not require a Light Sleep instance to report `STOPPED`; status alone may not identify the sleep tier.

### Bounded Idle Observation Protocol
To observe a service entering sleep without breaking production traffic:
1. Note the configured idle delay $T_{\text{delay}}$.
2. Wait passively for $T_{\text{delay}} + \text{buffer}$ (e.g., 6 minutes for a 5-minute timeout) without issuing data-plane HTTP requests. Set an observation deadline and report progress; stop and investigate if no transition appears by the deadline.
3. Query `koyeb instances list` via the launcher to inspect current instance states.
4. If instances remain active, check logs for background keep-alives or external pingers.

---

## 5. Wake Testing & Latency Metrics

To test wake-up behavior, issue a single controlled HTTP request to the designated health path and observe the wake transition:

```bash
# Issue one waking request
curl --http1.1 --max-time 60 -o /dev/null -s -w "HTTP_STATUS: %{http_code}\nTIME_TOTAL: %{time_total}s\nTIME_STARTTRANSFER: %{time_starttransfer}s\n" \
  https://example-app.koyeb.app/health
```

### Latency Metric Disaggregation
Never blend distinct platform phases into a single arbitrary "speedup" claim:
1. **Platform Wake / Hypervisor Resume Time**: Time taken by Koyeb hypervisor to resume snapshot (Light) or initialize microVM (Deep).
2. **Container Created-to-Healthy Time**: Time from container boot until application health check passes.
3. **HTTP/1.1 TTFB (Time to First Byte)**: Network transit + platform wake + server request processing.
4. **Full Response / AI Model Generation Time**: Duration until the entire response payload or streaming token stream is finished.

*Note*: Comparing differing measurement clocks or conflating TTFB with complete AI response durations produces invalid metrics.

---

## 6. Cost Considerations

- Sleep-to-zero capabilities reduce instance run time and resource consumption.
- Pricing, free allowances, and billing units are determined by active Koyeb pricing policies and terms of service.
- Statements in preview documentation do not constitute permanent billing guarantees. Always refer users to official [Koyeb Pricing](https://www.koyeb.com/pricing) and actual invoice line items.
- Never execute automated platform-wide sleep modifications without explicit user task authorization.
