# Vault Audit Logging Configuration

## Audit Device Enablement

Vault's audit devices are the mechanism through which all request and response data is logged. An audit device must be configured and enabled before any other Vault operations are recorded.

### Enable an Audit Device

```hcl
# File-based audit device
audit "file" {
  path = "/var/log/vault/audit.log"
  mode = "0640"
}

# Socket-based audit device
audit "socket" {
  path = "/var/run/audit.sock"
  mode = "0640"
}

# Syslog-based audit device
audit "syslog" {
  mode = "0640"
  facility = "local0"
  tag = "vault-audit"
}
```

Enable the device via the CLI after writing the configuration:

```bash
vault audit enable file path=/var/log/vault/audit.log
vault audit enable socket path=/var/run/audit.sock
vault audit enable syslog
```

### Verify Audit Device is Active

```bash
vault audit list
```

Expected output includes the enabled device(s), e.g.:

```
Output: file            path=/var/log/vault/audit.log mode=0640
      socket            path=/var/run/audit.sock mode=0640
      syslog            mode=0640 facility=local0 tag=vault-audit
```

## Audit Log Storage

Vault supports three primary audit log storage mechanisms, each suited to different deployment patterns:

### File Storage

- **Path**: Configured via the `path` parameter in the audit device definition
- **Format**: JSON Lines (one JSON object per line) by default
- **Permissions**: Set via the `mode` parameter (octal, e.g., `0640`)
- **Best practice**: Write to a dedicated, regularly rotated volume or partition
- **Example HCL**:

```hcl
audit "file" {
  path = "/var/log/vault/audit.log"
  mode = "0640"
}
```

### Socket Storage

- **Path**: Unix domain socket path via the `path` parameter
- **Format**: JSON Lines, piped to a consumer process
- **Use case**: Real-time streaming to log shippers (Filebeat, Fluentd, etc.)
- **Example HCL**:

```hcl
audit "socket" {
  path = "/var/run/audit.sock"
  mode = "0640"
}
```

### Syslog Storage

- **Format**: Syslog RFC 5424 over UDP/TCP
- **Facility**: Configurable via the `facility` parameter (e.g., `local0` through `local7`)
- **Tag**: Identifies the source via the `tag` parameter
- **Use case**: Integration with syslog-ng, rsyslog, or centralized log platforms
- **Example HCL**:

```hcl
audit "syslog" {
  mode = "0640"
  facility = "local0"
  tag = "vault-audit"
}
```

## Log Formatting

Vault audit logs are structured as JSON objects, one per line. Each log entry contains the following standard fields:

| Field | Description |
|---|---|
| `time` | ISO 8601 timestamp of the request |
| `type` | Request type (`request`, `response`, `error`) |
| `role` | Vault role used for the request (if applicable) |
| `token` | Token ID used (masked in logs by default) |
| `request_id` | Unique identifier for the request |
| `operation` | API operation invoked |
| `path` | API path accessed |
| `request` | The original request payload (sanitized based on sensitivity) |
| `response` | The response from Vault |

### Custom Formatting with Go Templating

Vault supports custom log formatting via Go templating in the audit device configuration:

```hcl
audit "file" {
  path    = "/var/log/vault/audit.log"
  template = "{{.Time}} {{.Operation}} {{.Path}}"
}
```

Available template fields are documented in the Vault source and include all standard log fields plus any custom fields added via response wrapping.

## Retention

Audit log retention is critical for compliance and forensic analysis. Retention strategy depends on the storage mechanism:

### File-Based Retention

- **Rotation**: Use logrotate or external log rotation system
- **Retention period**: Configurable via logrotate `daily/weekly/monthly` cycles + `maxage`
- **Example logrotate configuration**:

```
/var/log/vault/audit.log {
  daily
  rotate 90
  compress
  delaycompress
  missingok
  notifempty
  create 0640 vault vault
  postrotate
    systemctl reload rsyslog >/dev/null 2>&1 || true
  endscript
}
```

This config retains 90 days of compressed audit logs.

### Syslog/Rsyslog Retention

- **Configuration**: `/etc/rsyslog.d/vault.conf` with `$ActionFileDefaultTemplate` and `$ActionFileRetentionLimit`
- **Retention**: Configured per the organization's compliance requirements (typically 1-7 years)
- **Best practice**: Ship logs to immutable storage before local deletion

### Immutable Retention with Object Lock

For compliance requirements (e.g., SOX, HIPAA, GDPR):

```hcl
# Archive audit logs to S3 with Object Lock
terraform {
  backend "s3" {
    bucket         = "org-audit-logs"
    key            = "vault/audit/${terraform.workspace}.tfstate"
    region         = "us-east-1"
    encrypt        = true
    acl            = "private"
    dynamodb_table = "terraform-state-lock"
    region         = "us-east-1"
  }
}

# S3 bucket policy with Object Lock
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ComplianceRetention",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObjectRetention",
      "Resource": "arn:aws:s3:::org-audit-logs/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-object-lock-mode": "COMPLIANCE",
          "s3:x-amz-object-lock-retain-until-date": "2025-11-26T00:00:00Z"
        }
      }
    }
  ]
}
```

This ensures audit logs cannot be deleted or modified for the retention period.

## Rotation

Audit log rotation prevents unbounded growth and maintains log usability.

### File Log Rotation

Managed externally via `logrotate` (as shown above) or through the log shipping agent's built-in rotation.

### Socket Log Rotation

- The socket consumer (Filebeat/Metricd) should be configured with its own rotation
- Ensure the socket path is cleaned up on rotation restart
- Use `copytruncate` mode if the consumer cannot handle log replacement gracefully

### Syslog Rotation

- Configured via rsyslog `$ActionRotateEvery` and `$ActionRotateMaxFiles`
- Ensure Vault's syslog process receives SIGHUP after rotation to reopen files

### Rotation Verification

```bash
# Check last rotation timestamp
ls -la /var/log/vault/audit.log*
# Verify log file is not growing unboundedly
watch -n 60 ls -lh /var/log/vault/audit.log
```

## Integration with External SIEM Systems

Vault audit logs can be forwarded to external SIEM platforms (Splunk, Elasticsearch, Sentinel, QRadar, etc.) via several methods:

### Filebeat/Metricbeat Integration

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/vault/audit.log
  json.keys_under_root: true
  json.add_error_key: true
  json.message_key: message

output.logstash:
  hosts: ["logstash.example.com:5044"]
  ssl.certificate: "/path/to/cert.crt"
  ssl.key: "/path/to/key.key"

outputelasticsearch:
  hosts: ["es.example.com:9200"]
  index: "vault-audit-%{+yyyy.MM.dd}"
```

### Syslog Forwarding

```hcl
# Vault syslog configuration
audit "syslog" {
  mode    = "0640"
  facility = "local0"
  tag     = "vault-audit"
  # Additional syslib parameters can be added here
}
```

Configure the syslog daemon to forward `local0` to the SIEM:

```bash
# rsyslog.d/vault.conf
local0.info     @@192.168.1.100:514
local0.warning  @@192.168.1.100:514
local0.err      @@192.168.1.100:514
```

### Direct TCP/UDP JSON Forwarding

```hcl
# Custom template for JSON forwarding
audit "file" {
  path    = "/var/log/vault/audit.log"
  template = "{{.Time}}\\n"
}
```

Ship the file directly via Logstash, Fluentd, or custom scripts:

```bash
# Example Logstash pipeline
input {
  file {
    path => "/var/log/vault/audit.log"
    start_position => "beginning"
    sincedb_path => "/var/lib/logstash/sinldb/vault-audit"
  }
}
filter {
  json {
    source => "message"
  }
}
output {
  elasticsearch {
    hosts => ["es.example.com:9200"]
    index => "vault-audit-${+yyyy.MM.dd}"
  }
}
```

### HMAC-Verified Forwarding

For integrity validation during SIEM ingestion, compute an HMAC-SHA256 digest over each log entry and include it as a verified field:

```
audit_entry_hmac = hmac_sha256(key, json_encode(entry))
```

The HMAC key must be shared out-of-band between Vault and the SIEM ingestion pipeline.

## Audit Hash Format and HMAC Verification

### Hash Format

Each audit log entry includes a SHA-256 hash of the raw JSON line, computed over the canonical form before any forwarding modifications. This allows recipients to verify log integrity.

### HMAC Verification Procedure

1. **Key establishment**: Share an HMAC key between Vault and the SIEM pipeline via a secure channel (e.g., AWS KMS, HashiCorp Vault transit, out-of-band exchange)
2. **Per-entry HMAC**: For each audit log line, compute:

```python
import hmac
import hashlib
import json

# Raw line from audit log
raw_line = '{"time":"2024-01-15T10:30:00Z","type":"request","operation":"read","path":"secret/data/app"}'

# Shared key (32 bytes minimum, base64-encoded)
key = base64.b64decode(" shared-hmac-key-base64-value==")

# Compute HMAC-SHA256
hmac_digest = hmac.new(key, raw_line.encode("utf-8"), hashlib.sha256).hexdigest()

print(f"hmac: {hmac_digest}")
# Output: hmac: 3a7d4e9f...
```

3. **Verification at SIEM**: The SIEM pipeline recomputes the HMAC over the received raw line and compares against the embedded `hmac` field. A mismatch indicates tampering or corruption.

4. **Include HMAC in log entry** (via custom template):

```hcl
audit "file" {
  path    = "/var/log/vault/audit.log"
  template = "{{.Time}}\" hmac=\"{{hmac .Data}}\\n"
}
```

The `{{hmac .Data}}` function computes HMAC-SHA256 over the structured data. The key must be configured globally or per-audit device.

5. **Verification at rest**: When archiving audit logs to immutable storage (S3 with Object Lock), also store the HMAC digest in a separate manifest file, enabling post-hoc integrity checks:

```bash
# Generate manifest
cd /archive/vault-audit
for f in *.log; do
  h=$(hmac-sha256 -k "$SHARED_KEY" "$f")
  echo "$h  $f" >> SHA256SUMS
done
```

### Audit Entry Structure with HMAC

A complete audit log entry with embedded HMAC:

```json
{
  "time": "2024-01-15T10:30:00Z",
  "type": "request",
  "role": "root",
  "token": "va_token_PxYZABc123",
  "request_id": "12345678-1234-1234-1234-123456789012",
  "operation": "read",
  "path": "secret/data/app",
  "request": {
    "client_token": "va_token_PxYZABc123",
    "display": "true"
  },
  "response": {
    "auth": null,
    "data": null,
    "wrap_info": null,
    "errors": null
  },
  "hmac": "3a7d4e9f8c2d1e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a"
}
```

The `hmac` field is computed over the canonical JSON representation of the entry (excluding the `hmac` field itself to avoid circular dependency).

## Configuration Checklist

- [ ] Audit device enabled (file, socket, or syslog) with `vault audit enable`
- [ ] `mode` set to restrict file permissions (0640 minimum)
- [ ] Retention policy defined (logrotate, rsyslog, or Immutable S3 Object Lock)
- [ ] Rotation schedule configured (daily/weekly via logrotate)
- [ ] SIEM integration configured (Filebeat, rsyslog, or direct TCP/UDP)
- [ ] HMAC key distributed and configured for integrity verification
- [ ] Custom log template includes `hmac` field if integrity verification required
- [ ] Quarterly audit review scheduled to validate log completeness and accuracy
- [ ] Archive protocol documented (S3 bucket with Object Lock COMPLIANCE mode, 365-day minimum)