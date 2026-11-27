# CoreDNS Forwarding

## A. Purpose and scope

Document CoreDNS forwarding: upstream resolvers, stub domains, conditional forwarding, split-horizon DNS for offline.

Cross-references `network-matrix/network-communication-matrix.md`, `network-matrix/coredns-forwarding.md`, `offline-artifacts/artifact-matrix.md`.

## B. CoreDNS configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        # Upstream resolvers for non-cluster domains
        forward . 10.20.0.53 10.20.0.54 {
            except cluster.local
        }
        # Stub domains for service discovery
        stubdomains:
          svc.cluster.local:
            - 10.20.0.53
            - 10.20.0.54
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

## C. Upstream resolvers

| Environment | Upstream | Source |
|-------------|----------|--------|
| Online | 1.1.1.1, 8.8.8.8 | Internet |
| Offline | 10.20.0.53, 10.20.0.54 | Internal DNS |
| Air-gapped | /etc/resolv.conf | Host DNS |

## D. Split-horizon DNS (offline)

In offline environments, CoreDNS forwards non-cluster queries to internal DNS servers that resolve from the local mirror:

```yaml
forward . 10.20.0.53 {
    except cluster.local
}
```

## E. Conditional forwarding

Conditional forwarding for service discovery across clusters:

```yaml
stubdomains:
  svc.east.cluster.local:
    - 10.50.0.53
  svc.west.cluster.local:
    - 10.60.0.53
```

## F. Cross-references

- `network-matrix/network-communication-matrix.md` — Network communication matrix
- `network-matrix/coredns-forwarding.md` — CoreDNS forwarding reference
- `offline-artifacts/artifact-matrix.md` — CoreDNS image
