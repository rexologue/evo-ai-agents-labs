```bash
docker buildx build --platform linux/amd64 -t agent-profiler -f Dockerfile ..
docker run --rm --network host --env-file .env agent-profiler
```