# Working State & Task Log

**Repository**: `grapeot/koyeb-skill`
**Current Phase**: Phase 1: Repository Scaffolding (Completed)
**Last Updated**: 2026-10-02

---

## 1. Changelog

- **2026-10-02**: Initialized repository scaffold.
  - Created core repository contracts: `README.md`, `AGENTS.md`, `.gitignore`, `.env.example`, `LICENSE`.
  - Created technical specification contracts in `docs/`:
    - `docs/prd.md`: Product requirements, scope boundaries, and execution contracts.
    - `docs/rfc.md`: Technical architecture, launcher specifications, and CLI v5.12.0 semantics.
    - `docs/test.md`: Offline test matrix, evals plan, and real-world edge case scenarios.
    - `docs/working.md`: Task tracker and milestone log.
  - Implementation of `scripts/koyeb_env.py`, `tests/test_koyeb_env.py`, `skills/koyeb/SKILL.md`, and evals are intentionally pending Phase 2.

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

### Phase 2: Launcher Implementation & Offline Testing (PENDING)
- [ ] Implement `scripts/koyeb_env.py` using Python 3.10+ standard library only:
  - [ ] Strict `.env` subset grammar parser.
  - [ ] 1Password CLI `op read` integration via subprocess.
  - [ ] Argument validator rejecting `--token`, `--debug-full`, and `--url`.
  - [ ] Sanitized error reporting and token masking.
  - [ ] Native child exit code and stdio preservation.
- [ ] Implement `tests/test_koyeb_env.py` with offline subprocess stubs:
  - [ ] Test literal token resolution.
  - [ ] Test 1Password URI resolution.
  - [ ] Test missing/empty token handling.
  - [ ] Test prohibited flag interception.
  - [ ] Test exit code propagation and argument forwarding.

### Phase 3: Skill Implementation (PENDING)
- [ ] Implement root skill `skills/koyeb/SKILL.md` (~150-250 lines):
  - [ ] Progressive disclosure routing.
  - [ ] Launcher command shortcuts.
  - [ ] Core guardrails and verification loop.
- [ ] Implement reference modules:
  - [ ] `skills/koyeb/references/auth.md`
  - [ ] `skills/koyeb/references/inspect.md`
  - [ ] `skills/koyeb/references/changes.md`
  - [ ] `skills/koyeb/references/sleep.md`
  - [ ] `skills/koyeb/references/fleet.md`

### Phase 4: Evals & Agent Verification (PENDING)
- [ ] Create `evals/evals.json` with scenario prompts and assertions.
- [ ] Validate prompt parsing across target agent harnesses.

### Phase 5: Publication & Integration (PENDING)
- [ ] Optional read-only smoke validation against staging account.
- [ ] Add root skill reference to agent index.
- [ ] Final security audit and git commit.

---

## 3. Key Design Invariants

1. **Zero External Runtime Dependencies**: The launcher must never require third-party Python packages (`requests`, `python-dotenv`, etc.). Python 3.10+ standard library is authoritative.
2. **Official CLI as Execution Engine**: No direct REST/GraphQL client implementation. The official Koyeb CLI binary (`v5.12.0+`) performs all cloud interactions.
3. **No Secret in Argv or Logs**: Credentials must never be passed via CLI arguments or printed in plain text.
4. **Fictional Examples Only**: Public documentation, tests, and examples must strictly use fictional placeholders (`example-app`, `example-service`, `example.com`, `replace-with-your-key`, `op://your-vault/your-item/your-field`).
