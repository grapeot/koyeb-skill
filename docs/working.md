# Working State & Task Log

**Repository**: `grapeot/koyeb-skill`
**Current Phase**: Implementation Verified; Pull Request Pending
**Last Updated**: 2026-10-02

---

## 1. Changelog

- **2026-10-02**: Initialized repository scaffold.
  - Created core repository contracts: `README.md`, `AGENTS.md`, `.gitignore`, `.env.example`, `LICENSE`.
  - Created technical specification contracts in `docs/`: `prd.md`, `rfc.md`, `test.md`, `working.md`.
- **2026-10-02**: Authored complete skill, references, evals, and documentation updates.
  - Created root skill `skills/koyeb/SKILL.md` (150 lines) with goal/outcome/resource/output-contract style.
  - Authored modular reference modules under `skills/koyeb/references/`:
    - `auth.md`: Launcher security boundary, strict `.env` parser grammar, 1Password `op read` integration, prohibited flags (`--token`, `--debug-full`, `--url`), and process exit codes.
    - `inspect.md`: Structured querying (`-o json`), pagination caveats (absence of `--limit`/`--offset`), bounded historical log queries, and HTTP 404 interpretation.
    - `changes.md`: Service updates, definition merging vs `--override`, image reuse via `--skip-build`, `--save-only` distinction, stdin secret creation, and custom domain CNAME discovery.
    - `sleep.md`: Dual-tier Light/Deep sleep architecture, `--min-scale 0` requirement, disabling tiers with `0`, idle resets via data traffic, safe control-plane queries, and wake benchmarking.
    - `fleet.md`: Multi-service orchestration, batch rollout protocols, stop-on-failure policy, external system boundaries, and resource deletion guardrails.
  - Created `evals/evals.json` containing 5 realistic evaluation scenarios with assertion criteria.
  - Authored pull request summary `.agent-pr-body.md`.
  - Updated `README.md`, `AGENTS.md`, `docs/prd.md`, `docs/rfc.md`, and `docs/test.md` from scaffold to implemented status.
   - **Verification Status**: All 12 offline tests passed. Read-only CLI 5.12.0 smoke checks verified 1Password resolution from a gitignored `.env`, service inspection, complete service listing, and bounded Light Sleep lifecycle log retrieval. No new live cloud mutations were performed during implementation verification.
   - Fact-drift review corrected unsupported zero-downtime guarantees, sleep-mode inference from instance status, invented snapshot storage details, and the misleading claim that `redeploy --skip-build` selects a historical deployment for rollback.

---

## 2. Project Roadmap & Checklist

### Phase 1: Repository Scaffolding & Specifications (COMPLETED)
- [x] Create project `LICENSE` (MIT, copyright 2026 grapeot).
- [x] Define `.gitignore` with strict secret, cache, and artifact exclusions.
- [x] Create `.env.example` with fictional literal and 1Password `op://` examples.
- [x] Create `README.md` with project purpose, prerequisites, installation guidance, and planned usage.
- [x] Create `AGENTS.md` with strict operational rules, privacy requirements, and state tracking.
- [x] Author `docs/prd.md` detailing functional and non-functional requirements.
- [x] Author `docs/rfc.md` defining launcher architecture and security model.
- [x] Author `docs/test.md` defining offline test suites, evals, and operational edge cases.
- [x] Author `docs/working.md` establishing state tracking.

### Phase 2: Launcher Implementation & Offline Testing (VERIFIED)
- [x] Implement `scripts/koyeb_env.py` using Python 3.10+ standard library only:
   - [x] Strict `.env` subset grammar parser rejecting duplicate keys and never evaluating shell interpolation.
  - [x] 1Password CLI `op read` integration via subprocess with 30s timeout and error suppression.
  - [x] Argument validator rejecting `--token`, `--debug-full`, and `--url`.
   - [x] Credential diagnostics omit values and suppress failed `op` output; native CLI streams remain unchanged.
  - [x] Native child exit code and stdio preservation.
- [x] Implement `tests/test_koyeb_env.py` with offline subprocess stubs (12 unit tests):
  - [x] Test literal token resolution.
  - [x] Test 1Password URI resolution.
  - [x] Test missing/empty token handling.
  - [x] Test prohibited flag interception.
  - [x] Test exit code propagation and argument forwarding.
- [x] Local offline suite executed and verified: 12 tests passed. Hosted CI will run on the implementation PR.

### Phase 3: Skill Implementation (COMPLETED)
- [x] Implement root skill `skills/koyeb/SKILL.md` (150 lines):
  - [x] Goal / outcome / resource / output-contract style.
  - [x] Progressive disclosure routing.
  - [x] Launcher command shortcuts.
  - [x] Core guardrails and verification loop.
  - [x] Allowlisted output report example.
- [x] Implement reference modules:
  - [x] `skills/koyeb/references/auth.md`
  - [x] `skills/koyeb/references/inspect.md`
  - [x] `skills/koyeb/references/changes.md`
  - [x] `skills/koyeb/references/sleep.md`
  - [x] `skills/koyeb/references/fleet.md`

### Phase 4: Evals Authored; Cross-Harness Benchmark Pending
- [x] Create `evals/evals.json` with 5 realistic scenario prompts and assertion criteria.
- [ ] Scenario prompt execution across target agent harnesses (pending verification by main).

### Phase 5: Publication & Integration (PENDING)
- [x] Authorized read-only smoke validation with official CLI 5.12.0; no private fixtures or log contents published.
- [ ] Final security audit and git commit.

---

## 3. Key Design Invariants

1. **Zero External Runtime Dependencies**: The launcher must never require third-party Python packages (`requests`, `python-dotenv`, etc.). Python 3.10+ standard library is authoritative.
2. **Official CLI as Execution Engine**: No direct REST/GraphQL client implementation. The official Koyeb CLI binary (`v5.12.0+`) performs all cloud interactions.
3. **No Secret in Argv or Logs**: Credentials must never be passed via CLI arguments or printed in plain text.
4. **Fictional Examples Only**: Public documentation, tests, and examples must strictly use fictional placeholders (`example-app`, `example-service`, `example.com`, `replace-with-your-key`, `op://your-vault/your-item/your-field`).
