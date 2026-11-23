# External DNS

External DNS publishes DNS records for Services and Ingresses to the internal DNS server.

## Symptom: DNS records not created

**Likely cause:** External DNS cannot reach the internal DNS API, or the source filter excludes the Service/Ingress.

**Fix:**
```bash
kubectl get externaldns -A
kubectl logs -n externaldns -l app=external-dns --tail=100
```

**Self-check:** `nslookup <service>.<zone>` from inside the cluster returns the Service IP.

**Ponytail:** Scope ceiling — External DNS install and basic record creation. Add multiple DNS providers, zone filtering, and TLS certificate integration when those patterns are used.
