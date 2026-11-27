# Documentation Standards

This document defines the documentation conventions for the Cloud-Native Stack Implementation Guide. Every component guide should follow this structure.

## Document Structure

Every component guide must follow this 14-section structure:

```
# <Component Name>

Status: DRAFT | REVIEWED | ACCEPTED
Owner: <team>
Last reviewed: YYYY-MM-DD
Applies to version: <pinned version>
Source of truth: <official documentation URL + check date>

## 1. Purpose and Architecture
## 2. Supported Versions and Compatibility
## 3. Prerequisites
## 4. Network and Firewall Requirements
## 5. Installation
## 6. Configuration
## 7. Air-Gap Installation
## 8. Validation and Health Checks
## 9. Monitoring and Alerting
## 10. Upgrade
## 11. Migration
## 12. Backup and Restore
## 13. Troubleshooting
## 14. Rollback and Limitations
```

## Section Guidelines

### 1. Purpose and Architecture
- **Purpose**: What problem this component solves in this platform
- **Architecture**: How it is arranged (include Mermaid diagram if useful)
- **Dependencies**: What it needs, what it must not depend on
- **Deployment Location**: Which role/cluster it runs in
- **Recommended Production Model**: The configuration used in production
- **Alternatives & Decision Criteria**: What else was considered, when the alternative would win. Link the ADR.

### 2. Supported Versions and Compatibility
| Item | Requirement |
|---|---|
| OS | |
| Version | |
| CPU | |
| RAM | |
| Storage | |
| Network | |
| Dependencies | |
| Licensing | |
| Compatibility Constraints | |

Compatibility table with check date and source URL. Anything not verified is marked **UNVERIFIED** with the verification procedure.

### 3. Prerequisites
- Infrastructure dependencies
- Software dependencies
- Configuration prerequisites
- Credentials and secrets needed

### 4. Network and Firewall Requirements
- Required inbound/outbound ports
- Network segments and VLANs
- DNS requirements
- Load balancer requirements

### 5. Installation
- **Prerequisites**
- **Execution Context**: Which host/cluster the commands run on
- **Privileges**: Required capabilities
- **Ordered Commands**: Numbered, runnable
- **File Paths**: Every file that is written
- **Configuration Examples**: Actual YAML/values, with sanitized example
- **Parameter Explanations**: What each key does
- **Environment-Specific Values**: Which values change per environment

### 6. Configuration
- Configuration file examples (sanitized)
- Key parameter explanations
- Environment-specific overrides
- Integration with platform systems (Vault, monitoring, etc.)

### 7. Air-Gap Installation
- Official sources (URLs)
- Packages: names and versions
- Images: full image paths and tags
- Charts: chart and version
- Plugins: names and versions
- Transitive dependencies: the full closure
- Internal repository mapping: source -> internal path
- Integrity verification: exact command
- Required client configuration: files that change

### 8. Validation and Health Checks
- **Health Checks**: Commands and expected output
- **Expected Outputs**: Literal examples
- **Functional Tests**
- **Failure Tests**: What happens when a dependency is down
- **Performance Tests**: Benchmark and numbers to beat
- **Automated Validation**: Script and where it runs

### 9. Monitoring and Alerting
- Exposed metrics and endpoints
- Key alerts with runbook links
- Dashboard references
- SLO/SLI definitions

### 10. Upgrade
- Upgrade path and prerequisites
- Step-by-step upgrade procedure
- Rollback procedure
- Breaking changes and migration notes

### 11. Migration
- Migration scenarios
- Data migration procedures
- Compatibility considerations
- Cutover procedures

### 12. Backup and Restore
- What is backed up
- Backup frequency and retention
- Restore procedure (tested)
- RTO/RPO targets

### 13. Troubleshooting
- Link to troubleshooting runbook
- Common failure modes
- Diagnostic commands
- Escalation paths

### 14. Rollback and Limitations
- What can be rolled back
- What cannot be rolled back
- Known limitations
- Disaster recovery scenario and procedure

## Writing Conventions

### Commands and Examples
- **Copy/paste friendly**: Every command must be directly runnable
- **Explicit placeholders**: Use `<PLACEHOLDER>` format, explain every value
- **Context**: State execution context (which host, cluster, namespace)
- **Privileges**: State required capabilities (sudo, cluster-admin, etc.)

### Formatting
- Use **bold** for UI elements, **`code`** for commands/paths
- Tables for structured data
- Mermaid diagrams for architecture
- Numbered lists for ordered procedures

### Placeholders
Use `<UPPERCASE_PLACEHOLDER>` format with clear descriptions:
```yaml
server: "<VAULT_SERVER_URL>"  # e.g., https://vault.internal:8200
```

### Language
- English and Persian technical content must be equivalent
- Shared scripts and configuration — do not create two independent implementations
- Cross-links between language versions
- Missing translations detectable via `tests/test_repo_tools.py`

## Metadata Requirements

Every document must include:
```markdown
Status: DRAFT | REVIEWED | ACCEPTED
Owner: <team>
Last reviewed: YYYY-MM-DD
Applies to version: <pinned version>
Source of truth: <official documentation URL + check date>
```

## Status Values

| Status | Meaning |
|---|---|
| **DRAFT** | Initial draft, not reviewed |
| **REVIEWED** | Reviewed by owner, may have open comments |
| **ACCEPTED** | Approved for production use |

## Cross-References

- Link ADRs: `[ADR-0017](../decisions/ADR-0017-pki-and-certificate-ownership.md)`
- Link version matrix: `[Version Matrix](../compatibility/version-matrix.md)`
- Link platform standards: `[Platform Standards](../requirements/platform-standards.md)`

## Validation

Run `python3 tests/test_repo_tools.py` to check:
- Markdown links
- Mermaid syntax
- English/Persian cross-links
- No invented version claims
- Broken references

## Changelog

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-11-23 | 1.0 | Initial documentation standards | Platform Team |
