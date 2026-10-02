# Multi-Service Fleet & External Runbook Reference

This reference covers managing multi-service application topologies, batch deployment protocols, stop-on-failure execution, resource deletion guardrails, and boundaries with external systems.

---

## 1. Fleet Topologies & Discovery

An application on Koyeb can contain multiple interdependent services (e.g., API gateway, background queue worker, caching layer, web frontend).

### Topology Discovery
Discover services within an application dynamically without assuming hardcoded project structures:
```bash
# Query all services within an application
python3 scripts/koyeb_env.py -- services list --app example-app -o json
```

### Local Workspace Routing & Policy Discovery
- Never bake specific project names, service topologies, or regional preferences into public skill definitions.
- Agents discover application-specific defaults (such as instance sizes, regions, and environment dependencies) by reading workspace guides:
  1. Workspace rules (`AGENTS.md`, `CLAUDE.md`, or `WORKSPACE.md`).
  2. Local environment overlay (`.env`).
  3. Dedicated project runbooks (e.g. `docs/deploy.md` or `docs/runbook.md`).

---

## 2. Batch Operations Protocol

When a task requires mutating multiple services across an application (such as rolling out environment updates or synchronizing scaling policies), agents must adhere to the following protocol:

### Step 1: Explicit Target Enumeration
- Enumerate explicit target service names (`example-app/web`, `example-app/worker`).
- Never perform implicit wildcard bulk updates or iterate over unverified lists.

### Step 2: Plan Grouping & Dependency Ordering
- Calculate the configuration delta for each service.
- Group operations in dependency order (e.g., data migrations / worker background services before user-facing web routing).

### Step 3: Bounded Step-by-Step Application
- Execute updates one service at a time with bounded timeouts:
  ```bash
  python3 scripts/koyeb_env.py -- services update example-app/worker \
    --env WORKER_CONCURRENCY=4 \
    --skip-build --wait --wait-timeout 5m
  ```

### Step 4: Step-by-Step Verification & Stop-on-Failure
- Verify service health (`HEALTHY`) immediately after each step.
- **Stop-on-Failure Policy**: If any service update fails or times out:
  1. Terminate the batch rollout immediately.
  2. Do not proceed to subsequent services.
  3. Record the exact failure point and the rollback command in the output report.
  4. Execute rollback for the failing service if authorized.

---

## 3. External System Boundaries

Koyeb hosts compute and ingress workloads, but modern applications frequently interact with external cloud resources:

| External System | Boundary Division | Responsibility |
| :--- | :--- | :--- |
| **External Databases** (Supabase, Neon, Cloud SQL) | Koyeb stores connection strings in encrypted `secrets`. | Database migrations, schemas, and provisioning belong to project database runbooks. |
| **DNS Registrars / Proxies** (Cloudflare, AWS Route53) | Koyeb provides the CNAME target via `domains get`. | Pointing public DNS records to Koyeb CNAMEs belongs to project DNS runbooks. |
| **Identity Providers** (Auth0, Clerk, Logto) | Koyeb services receive auth tokens via HTTP headers. | Configuring redirect URIs and client secrets belongs to project identity runbooks. |

**Rule**: Agents must never attempt to issue cloud provider commands (such as AWS, Cloudflare, or database CLI tools) within a Koyeb context. Output the verified Koyeb endpoint or CNAME and instruct the user or delegate to the appropriate project runbook.

---

## 4. Deletion & Teardown Guardrails

Resource deletion commands permanently destroy infrastructure:
```bash
# Delete a service
python3 scripts/koyeb_env.py -- services delete example-app/example-service

# Delete an entire application
python3 scripts/koyeb_env.py -- apps delete example-app
```

### Deletion Rules
1. **Target Authorization**: When the user explicitly authorizes deletion of a named resource, proceed without redundant confirmation dialogues.
2. **Koyeb Scope Isolation**: A Koyeb delete command **only** removes Koyeb resources.
3. **Entwined Dependencies**: If the service or application connects to an external database or reverse proxy, inspect the project runbook before deleting to ensure external resources are cleanly unlinked or decommissioned.
