# Ansible Idempotency Test Suite

## Changed-When Assertions

`changed_when` controls how Ansible reports a task when a command exits with a success code but the underlying state has not actually changed. This is critical for tasks that wrap non-idempotent commands.

**Rules:**

- Prefer Ansible modules over `shell`/`command` wherever a module exists. Modules are inherently idempotent.
- Where a shell command is unavoidable, attach `changed_when: false` if the command is naturally idempotent (e.g. `sysctl -w`), or provide a meaningful condition that indicates actual state change.
- Never leave a `shell` task without `changed_when` — a bare `shell` always reports `changed: true` on execution.

**Example — correctly guarded task:**

```yaml
- name: Ensure the containerd registry mirror is configured
  ansible.builtin.template:
    src: hosts.toml.j2
    dest: /etc/containerd/certs.d/{{ item }}/hosts.toml
    owner: root
    group: root
    mode: "0644"
  loop: "{{ containerd_registries }}"
  notify: restart containerd
```

**Example — incorrectly guarded task:**

```yaml
# Wrong: always reports changed
- name: Set sysctl
  ansible.builtin.shell: sysctl -w {{ item.key }}={{ item.value }}
  loop: "{{ sysctl_settings }}"
```

The correct form uses `ansible.posix.sysctl`, which is idempotent and persists the value.

**When to use `changed_when`:**

```yaml
- name: Run a custom health-check script
  ansible.builtin.shell: /usr/local/bin/health-check.sh
  changed_when: "result.rc == 0 and 'HEALTHY' in result.stdout"
  register: health_check
```

Reference: `ansible-structure.md` §Idempotency for the full idempotency rules and guard patterns.

---

## Idempotency Verification

Ansible playbooks are re-run routinely in production and CI. A second consecutive run must report **0 changed tasks**. A non-zero changed count on a no-op run is a defect.

**Verification workflow:**

1. **Syntax check**

   ```bash
   ansible-playbook -i inventories/staging/hosts.ini site.yml --syntax-check
   ```

2. **Lint**

   ```bash
   ansible-lint playbooks/ roles/
   ```

3. **Dry-run (check mode)**

   ```bash
   ansible-playbook -i inventories/staging/hosts.ini site.yml --check --diff
   ```

4. **Full run — first pass**

   ```bash
   ansible-playbook -i inventories/staging/hosts.ini site.yml
   ```

5. **Full run — second pass (idempotency validation)**

   ```bash
   ansible-playbook -i inventories/staging/hosts.ini site.yml
   ```

   **Expected:** recap shows 0 changed, 0 failed

6. **Post-run verification**

   ```bash
   ansible all -i inventories/staging/hosts.ini -m setup
   ```

**Defect signs:**

- Second run reports `changed: [n]` where n > 0
- Tasks without `changed_when` on non-module commands
- Resources that are not truly idempotent (e.g. `command` without module guard)

Cross-references: `pipeline.md` §validate:ansible-idempotency for CI gate; `test-registry.md` P-02 for the acceptance test; `acceptance-criteria.md` P-02 for the requirement.

---

## Test Playbooks

The suite includes representative playbooks that demonstrate idempotent task patterns. Each playbook can be run twice to verify 0 changed on the second run.

### base.yml — OS baseline

Imports roles for package management, user setup, SSH hardening, and hostname configuration. All tasks use modules (`apt`, `yum`, `user`, `authorized_key`) with no bare `shell` commands.

### security.yml — Security hardening

Uses `ansible.posix.sysctl`, `ansible.builtin.firewalld`, and `ansible.builtin.line_in_file` for idempotent state management. No `shell` commands without `changed_when`.

### identity.yml — Identity setup

Uses `community.general.hashi_vault` lookup for credentials; no secret values in playbook source.

### containerd.yml — Container runtime

Configures containerd with `ansible.builtin.template` for config files and `ansible.builtin.service` for runtime management. Registry mirrors are set idempotently via `line_in_file` or `template`.

### kubernetes.yml — Kubespray wrapper

Wraps Kubespray playbooks via `ansible.builtin.import_playbook`. All Kubespray-managed resources are inherently idempotent.

**Running the idempotency check:**

```bash
# From the repo root
ansible-playbook -i automation/ansible/inventories/staging/hosts.ini automation/ansible/site.yml --check --diff

# Second run, must report 0 changed
ansible-playbook -i automation/ansible/inventories/staging/hosts.ini automation/ansible/site.yml
```

Verification output recap should show:

```
PLAY RECLOSED
ok=X   changed=0   unreachable=0   failed=0
```

Reference `ansible-structure.md` §Idempotency for the complete rule set and guard patterns.

---