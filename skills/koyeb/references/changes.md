# Service Changes, Deployments & Configuration Reference

This reference documents authorized patterns for creating services, updating configurations, mounting secrets, registering custom domains, redeploying, and planning rollback.

---

## 1. Service Creation & Verified Syntax

When creating a new service, use the official verified flag syntax:
- Use the documented plural port and route flags: `--ports <port>:<protocol>` and `--routes <path>:<port>` rather than relying on singular aliases.
- Instance types and regions must be selected based on project policy or user instructions. The example uses fictional app/repository identifiers and explicitly chosen `nano` and `fra` values; these are real platform options, not global recommendations.

```bash
# Create service from Git repository
python3 scripts/koyeb_env.py -- services create example-service \
  --app example-app \
  --git github.com/example/example-app \
  --git-branch main \
  --git-builder docker \
  --ports 8000:http \
  --routes /:8000 \
  --instance-type nano \
  --regions fra
```

### Source Integrity & Existing Definitions
When an existing service configuration needs modification:
- Do not silently delete and recreate a service to change its source. That changes service identity and may affect project bindings; if in-place updates are unsupported, explain the evidence and obtain authorization for the broader operation.
- Inspect the existing source with `services get example-app/example-service -o json` and perform an in-place update.

---

## 2. Service Updates: Merge vs. `--override`

By default, `koyeb services update` **merges** specified flags into the existing service definition.

```bash
# Standard update: merges new environment variables or limits while preserving existing config
python3 scripts/koyeb_env.py -- services update example-app/example-service \
  --env LOG_LEVEL=debug \
  --skip-build \
  --wait
```

### The `--override` Flag
- The `--override` flag completely replaces the entire service configuration with the provided arguments, stripping any unmentioned environment variables, routes, or ports.
- **Rule**: Never use `--override` routinely. Use `--override` only when explicitly instructed to overwrite the complete specification.

---

## 3. Deployment Mechanics: Rebuilds, `skip-build`, and `save-only`

### A. Fast Redeployment with `--skip-build`
When updating environment variables, scaling limits, or sleep delays that do not require recompiling code or re-pulling base layers, pass `--skip-build`:
```bash
python3 scripts/koyeb_env.py -- services redeploy example-app/example-service --skip-build --wait
```
- `--skip-build` instructs the Koyeb orchestrator to reuse the existing container image from the last successful deployment.
- This creates a new deployment while bypassing the build stage; provisioning and health checks still take time.

### B. Full Rebuilds
- When updating Git branches, Dockerfile paths, build arguments, or application source code, do **not** pass `--skip-build`. A full build is required.

### C. The `--save-only` Flag
- Passing `--save-only` writes the definition changes to the Koyeb control plane but does **not** trigger a live deployment.
- **Reporting Invariant**: Agents must never report a `--save-only` change as active or running in production. Live verification requires verifying that a deployment reached `HEALTHY`.

### D. Synchronous Wait Flags
Always specify `--wait` with a bounded `--wait-timeout` (e.g. `5m`) when programmatic verification is needed immediately:
```bash
python3 scripts/koyeb_env.py -- services update example-app/example-service \
  --min-scale 1 --max-scale 3 \
  --skip-build --wait --wait-timeout 5m
```

---

## 4. Application Runtime Secrets

Do not confuse the launcher management token (`KOYEB_API_KEY`) with application runtime secrets needed by your service (e.g., database URLs, payment keys).

### Creating Runtime Secrets
Always pass secret values via stdin to avoid capturing secrets in process tables:
```bash
echo "replace-with-your-runtime-secret" | python3 scripts/koyeb_env.py -- secrets create EXAMPLE_SECRET --value-from-stdin
```

### Attaching Secrets to Services
Reference the created secret inside the service environment using the `{{secret.NAME}}` interpolation syntax:
```bash
python3 scripts/koyeb_env.py -- services update example-app/example-service \
  --env 'DATABASE_URL={{secret.EXAMPLE_SECRET}}' \
  --skip-build --wait
```
- Existing secret references are preserved across routine updates.
- Avoid calling `koyeb secrets reveal`, as it outputs raw secret text to the terminal.

---

## 5. Custom Domains & External DNS

Koyeb provisions automated TLS certificates for custom domains.

```bash
# Register custom domain and attach to application
python3 scripts/koyeb_env.py -- domains create example.com --attach-to example-app

# Inspect domain metadata to obtain the intended CNAME target
python3 scripts/koyeb_env.py -- domains get example.com -o json
```

### Boundary with External DNS
- The JSON output from `domains get` provides `intended_cname` (e.g., `example.com.koyeb.app`).
- Koyeb does **not** manage external DNS providers (e.g., Cloudflare, Route53, Namecheap).
- **Rule**: Do not attempt to reconfigure external DNS providers through Koyeb CLI. Report the intended CNAME target in your output report and refer DNS record updates to the project DNS runbook.

---

## 6. Pause, Resume, and Rollback Procedures

### Pause & Resume
```bash
# Pause service (stops all running instances)
python3 scripts/koyeb_env.py -- services pause example-app/example-service

# Resume service
python3 scripts/koyeb_env.py -- services resume example-app/example-service
```
*Note*: Authorized pause/resume tasks proceed immediately without redundant reconfirmation.

### Rollback Procedure
If a new deployment fails or introduces regressions:
1. Identify the previous successful deployment ID:
   ```bash
   python3 scripts/koyeb_env.py -- deployments list --app example-app --service example-app/example-service -o json
   ```
2. Retrieve the definition of the prior deployment:
   ```bash
   python3 scripts/koyeb_env.py -- deployments get <prior-deployment-id> -o json
   ```
3. Restore the known-good configuration or explicitly select its built image using the installed CLI's supported update options, then deploy and verify. `redeploy --skip-build` alone reuses the last successful build; it does not select the historical deployment retrieved above and is not a generic rollback command. Preserve project runtime secret references and account for database/schema compatibility in the project runbook.
