# LLM Inference Troubleshooting

## Symptoms

- Inference server not responding
- GPU out of memory (OOM)
- Model not loading
- High latency / low throughput
- Requests timing out

## Likely causes

- Inference server (TGI/vLLM) not running
- GPU not allocated to workload
- Model weights not downloaded or cached
- Wrong GPU device visible to container
- Concurrent requests exceeding capacity

## Diagnostic commands

```bash
# Is inference server running?
kubectl -n <namespace> get pods -l app=<inference-app>
kubectl -n <namespace> logs -l app=<inference-app>

# Is GPU visible?
kubectl -n <namespace> exec <pod> -- nvidia-smi
kubectl -n <namespace> exec <pod> -- cat /proc/driver/nvidia/gpus/0/information

# Is model cached?
kubectl -n <namespace> exec <pod> -- ls -la /models/
kubectl -n <namespace> exec <pod> -- ls -la /root/.cache/huggingface/

# Test inference endpoint
curl -X POST <inference-url>/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "<model>", "prompt": "Hello", "max_tokens": 10}'

# Check GPU memory
kubectl -n <namespace> exec <pod> -- nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

## Expected healthy state

- Inference server pods: Running, 0 restarts
- `nvidia-smi` shows GPU with memory available
- Model weights present in cache directory
- Inference endpoint returns 200 OK
- GPU memory usage within limits

## Remediation

- Restart inference server: `kubectl rollout restart deployment/<inference-app>`
- Add GPU resource requests/limits to pod spec
- Download/model cache: pre-pull model weights
- Fix NVIDIA device plugin: `kubectl get daemonset -n kube-system -l app=nvidia-device-plugin-daemonset`
- Reduce batch size or concurrent requests

## Risks

- Restarting inference server interrupts active requests
- Changing GPU allocation can evict other workloads
- Downloading large models consumes network bandwidth and storage

## Verification

```bash
kubectl -n <namespace> get pods -l app=<inference-app>
kubectl -n <namespace> exec <pod> -- nvidia-smi
curl -sf <inference-url>/v1/models | python3 -m json.tool | head -10```
