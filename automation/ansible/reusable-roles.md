# Reusable Ansible Roles

## Role Structure

Every reusable role follows a standardized directory layout to ensure discoverability and consistency across the infrastructure codebase.

```text
roles/
├── <role-name>/
│   ├── defaults/           # lowest priority variable values
│   │   └── main.yml        # default versions, features, package versions
│   ├── dependencies/       # roles that must be installed before this one
│   │   └── main.yml        # version-compatible dependency declarations
│   ├── files/              # static files deployed as-is (no templating)
│   │   └── ...             # checksummed binaries, configs, scripts
│   ├── handlers/           # handlers notified by role tasks
│   │   └── main.yml        # services, daemons, restart actions
│   ├── metadata/           # role versioning and Galaxy metadata
│   │   └── galaxy.yml      # name, description, author, company, min_ansible_version
│   ├── README.md           # role documentation: purpose, variables, examples
│   ├── tasks/              # ordered list of tasks
│   │   └── main.yml        # the core role logic
│   ├── templates/          # Jinja2-templated configuration files
│   │   └── ...             # .j2 files deployed to destination
│   ├── tests/              # testing infrastructure
│   │   ├── test.yml        # integration test playbook
│   │   └── inventory.yml   # test inventory (localhost by default)
│   └── tests/
│       └── molecule/       # Molecule testing framework directory
│           ├── convergence/
│           ├── molecule.yml
│           ├── setup/
│           ├── playbook.yml
│           └── verify/
```

### Minimal Required Files

Each role **must** include at minimum:

- `tasks/main.yml` — the role's task list
- `README.md` — documentation with variable descriptions and usage examples
- `metadata/galaxy.yml` — role metadata for Galaxy publishing and dependency resolution

All other directories are optional but encouraged for complete roles.

## Dependency Management

Roles declare dependencies in `dependencies/main.yml`. This file lists other roles that must be applied before the current role's tasks execute.

### Dependency Declaration

```yaml
# dependencies/main.yml
galaxy_info:
  author: Your Name
  company: Your Company
  description: Role that configures NTP
  company_url: https://yourcompany.com
  min_ansible_version: "2.14"

  galaxy_tags:
    - ntp
    - time
    - system

dependencies:
  - role: community.general.timezone
    version: ">=3.0.0"
  - role: hostname
    version: ">=1.2.0"
```

### Dependency Best Practices

- **Explicit version constraints** — always pin dependency versions using `version:` to prevent breaking changes from upstream updates
- **Directional dependencies** — if Role A depends on Role B, ensure the dependency is declared in Role A's `dependencies/main.yml`, not Role B's
- **Avoid circular dependencies** — validate the dependency graph with `ansible-galaxy role inspect-tags` before merging
- **Self-sufficient roles** — each role should function correctly even if dependencies are absent, with graceful degradation or clear error messages

### Dependency Validation

```bash
# Inspect a role's dependency tree
ansible-galaxy role inspect-tags --role-path roles/ntp --tags

# Lint dependencies
ansible-lint --offline --enable-plugins galaxy-tags roles/ntp
```

## Variable Design

Variables are the primary mechanism for customizing role behavior. Consistent variable design ensures roles are predictable and composable.

### Variable Priority Order (highest to lowest)

1. `vars/` directory — role-internal variables, rarely overridden
2. `default/main.yml` — lowest priority; can be overridden by user
3. `vars/main.yml` — medium priority; overrides defaults
4. `extra_vars` / `variable_files` — highest priority; user-controlled override

### Variable Naming Conventions

- **Prefix role-specific variables** with the role name to avoid collisions (e.g., `ntp::servers`, `containerd::registry_mirrors`)
- Use **lowercase_with_underscores** for all variable names
- Document every public variable in the role's `README.md`
- Mark internal variables with an underscore prefix (e.g., `_internal_cache_key`) to signal they are not part of the public API

### Variable Defaults

```yaml
# defaults/main.yml
ntp::servers:
  - "0.pool.ntp.org"
  - "1.pool.ntp.org"
  - "2.pool.ntp.org"
ntp::timezone: "UTC"
containerd::log_level: "info"
```

### Variable Documentation

Each variable in `README.md` should include:

- **Description**: What the variable configures
- **Default**: The default value (if any)
- **Required**: Whether the variable must be provided
- **Type**: String, list, boolean, integer, or JSON object
- **Example**: A concrete usage example

## Idempotency Patterns

Ansible roles must be fully idempotent — repeated execution must converge to 0 changed tasks.

### Core Idempotency Rules

1. **Prefer modules over `shell`/`command`** — built-in modules are idempotent by design
2. **Guard all shell commands** — use `changed_when` with a meaningful condition, or `creates`/`removes` for file operations
3. **Never use bare `command`** — only `ansible.builtin.command` with `changed_when: false` when the command is inherently idempotent (e.g., `sysctl -w`)
4. **Use `check mode` extensively** — `ansible-playbook --check --diff` must pass before any production run

### Common Pattern Examples

**Correct — module-based (idempotent):**

```yaml
- name: Ensure containerd registry mirror is configured
  ansible.builtin.template:
    src: hosts.toml.j2
    dest: /etc/containerd/certs.d/{{ item }}/hosts.toml
    owner: root
    group: root
    mode: "0644"
  loop: "{{ containerd_registries }}"
  notify: restart containerd
```

**Correct — guarded shell command:**

```yaml
- name: Set sysctl parameter
  ansible.builtin.sysctl:
    name: "{{ item.key }}"
    value: "{{ item.value }}"
    state: present
  loop: "{{ sysctl_settings }}"
```

**Incorrect — unguarded shell command:**

```yaml
- name: Set sysctl (will always report changed)
  ansible.builtin.shell: sysctl -w {{ item.key }}={{ item.value }}
  loop: "{{ sysctl_settings }}"
```

### Idempotency Verification Workflow

```bash
# 1. Syntax check
ansible-playbook -i inventories/staging/hosts.yml site.yml --syntax-check

# 2. Lint
ansible-lint playbooks/ roles/

# 3. Dry-run (check mode)
ansible-playbook -i inventories/staging/hosts.yml site.yml --check --diff

# 4. First run — record output
ansible-playbook -i inventories/staging/hosts.yml site.yml

# 5. Second run — must show 0 changed (idempotency validation)
ansible-playbook -i inventories/staging/hosts.yml site.yml

# Expected recap:
PLAY RECLOSED
ok=X   changed=0   unreachable=0   failed=0
```

## Role Testing Procedures

Each role must include a test suite to validate functionality, idempotency, and compatibility.

### Molecule Testing Framework

Modern roles use [Molecule](https://molecule.readthedocs.io/) for testing Ansible roles against multiple platforms and distributions.

#### Molecule Directory Structure

```text
roles/<name>/tests/molecule/
├── convergence/
├── molecule.yml          # scenario configuration
├── playbook.yml          # playbook to execute role tasks
├── setup/
│   └── __init__.py       # post-create setup scripts
├── verify/
│   └── __init__.py       # post-state verification scripts
└── inventory.yml         # test inventory (localhost by default)
```

#### Minimum molecule.yml Configuration

```yaml
dependency:
  name: galaxy
  role: ../..

driver:
  name: docker

platforms:
  - name: instance1
    image: docker.io/centos:9
    cpus: 2
    memory: 4GB

provisioner:
  name: ansible
  playbook: playbook.yml

verifier:
  name: testinfra

scenario:
  name: default

dependency:
  name: galaxy
```

#### Test Playbook Example

```yaml
# playbook.yml
- name: Converge the role
  hosts: all
  become: true
  roles:
    - role: <role-name>
      # role-specific variables
      ntp::servers:
        - "0.pool.ntp.org"
```

#### Running the Test Suite

```bash
# From the role directory
molecule test

# Individual phases
molecule converge    # run the playbook
molecule verify      # run verification tests
molecule check       # run ansible-lint and syntax check
molecule destroy     # clean up test instances
```

### Traditional Test Playbooks (Molecule-less)

Roles without Molecule still require a test playbook:

```yaml
# tests/test.yml
- name: Test role idempotency
  hosts: localhost
  become: true
  roles:
    - role: <role-name>
      # variables as needed

  tasks:
    - name: Verify idempotency — first run
      ansible.builtin.debug:
        msg: "First run recap: {{ ansible_run_stats }}"

    - name: Verify idempotency — second run
      ansible.builtin.debug:
        msg: "Second run recap: {{ ansible_run_stats }}"

# Run twice:
# ansible-playbook -i tests/inventory.yml tests/test.yml
# # second run must show 0 changed
```

### Acceptance Criteria for Role Acceptance

A role is considered production-ready when:

- [ ] All tasks use Ansible modules (no bare `shell`/`command` without idempotency guards)
- [ ] `changed_when` is set on every non-module task
- [ ] Molecule tests pass against at least one Linux distribution (Ubuntu, Debian, Rocky/Alma, AlmaLinux)
- [ ] Idempotency validation: second consecutive run reports 0 changed tasks
- [ ] `README.md` documents all public variables with defaults and examples
- [ ] `metadata/galaxy.yml` has correct name, version, and dependencies
- [ ] Lint passes: `ansible-lint` with no errors or warnings
- [ ] Syntax check passes: `ansible-playbook --syntax-check`
- [ ] Role can be installed via `ansible-galaxy install <role-name>`

## Release and Versioning

Roles follow [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **MAJOR** — incompatible API changes; bump when breaking changes are introduced
- **MINOR** — new functionality, backward-compatible additions; bump for new variables/tasks
- **PATCH** — bug fixes, internal changes, no new public-facing behavior

### Version Bumping

```bash
# Using galaxy-tag plugin
ansible-galaxy role init <role-name>  # creates skeleton with version 0.1.0

# After changes, bump patch
ansible-galaxy version bump --type patch

# Or manually edit metadata/galaxy.yml
galaxy_info:
  version: "2.3.1"
```

### Galaxy Publishing

```bash
# Tag and push a release
git tag v2.3.1
git push origin v2.3.1

# Publish to Ansible Galaxy
ansible-galaxy role publish <role-name>
```
