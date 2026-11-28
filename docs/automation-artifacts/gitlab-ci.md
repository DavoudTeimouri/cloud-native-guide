# GitLab CI Artifacts

## Purpose and scope

GitLab CI pipeline templates and job definitions for validation, staging, and production deployment. All artifacts live under `automation/gitlab-ci/`.

## Directory layout

```text
automation/gitlab-ci/
├── .gitlab-ci.yml                 # Top-level pipeline; includes shared templates
├── ci/
│   ├── templates/
│   │   ├── validate.yml           # Stages 1-8 (validation only)
│   │   ├── deploy-staging.yml     # Stages 9-10
│   │   └── deploy-prod.yml        # Stages 11-13
│   └── scripts/
│       ├── drift-report.sh        # Drift detection report
│       └── post-deploy-check.sh   # Post-deployment verification
└── gitlab-ansible-design.md       # Ansible-GitLab integration design
```

## Customization points

### .gitlab-ci.yml (top-level)

Edit stages and includes for your environment:

```yaml
stages:
  - source
  - lint
  - ansible
  - kubernetes
  - registry
  - deploy-staging
  - deploy-prod

include:
  - local:/ci/templates/validate.yml
  - local:/ci/templates/deploy-staging.yml
  - local:/ci/templates/deploy-prod.yml
```

| Customization | Where | When to change |
| --- | --- | --- |
| Stage list | `.gitlab-ci.yml` stages | You add/remove pipeline stages |
| Included templates | `.gitlab-ci.yml` include | You add new template files |
| Runner tags | Job `tags:` in templates | Your runners use different tags |
| Registry URL | Job variables | Your Harbor/Nexus address differs |
| Image tags | Job `image:` | You pin different images |

### CI/CD variables (set in GitLab project settings)

Never hardcode secrets in `.gitlab-ci.yml`. Configure in GitLab CI/CD → Settings → Variables:

| Variable | Purpose | Example |
| --- | --- | --- |
| `CI_REGISTRY_USER` | Registry username | `harbor-admin` |
| `CI_REGISTRY_PASSWORD` | Registry password | from Vault |
| `VAULT_ADDR` | Vault address | `https://vault.internal:8200` |
| `VAULT_TOKEN` | Vault auth token | from CI mask variable |
| `TARGET_CLUSTER` | Cluster to deploy | `management` or `application` |
| `ANSIBLE_INVENTORY` | Inventory file path | `production/hosts.ini` |

## Pipeline stages

| Stage | Purpose | Gate |
| --- | --- | --- |
| source | Branch policy, signed commits, template check | Protected branch, MR required |
| lint | YAML lint, markdown lint | Must pass |
| ansible | Syntax check + lint | Must pass |
| kubernetes | Kubespray dry-run | Must pass |
| registry | Image scan, push to Harbor | Must pass |
| deploy-staging | Deploy to staging | Manual approval |
| deploy-prod | Deploy to production | Manual approval + change window |

## How to run

### Validate locally (before push)

```bash
# Lint YAML
yamllint automation/gitlab-ci/.gitlab-ci.yml automation/gitlab-ci/ci/templates/

# Lint markdown
markdownlint-cli2 docs/automation/gitlab-ci/ --config .markdownlint.yaml

# Ansible syntax check
ansible-playbook -i automation/ansible/inventories/staging/hosts.ini \
  automation/ansible/site.yml --syntax-check
```

### Push to GitLab

```bash
git add automation/gitlab-ci/
git commit -m "Update CI pipeline"
git push origin main
```

## Related

- [Automation Artifacts overview](index.md)
- [Ansible artifacts](ansible.md)
- [Validation tools](python-scripts.md)
