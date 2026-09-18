# Independent hosting rollback

1. Identify the last known-good immutable image tag.
2. Confirm the external database and Redis endpoints are healthy; rollback does not restore stateful services.
3. Run `kubectl -n dsp set image deployment/dsp-api api=dsp-api:<known-good-tag>` and the equivalent command for `dsp-web`.
4. Wait for both rollouts: `kubectl -n dsp rollout status deployment/dsp-api --timeout=5m` and `kubectl -n dsp rollout status deployment/dsp-web --timeout=5m`.
5. Verify `/health/live`, `/health/ready`, `/metrics`, the web `/api/health`, and the authenticated application smoke suite.
6. If the release changed a database schema, follow the migration's documented rollback or forward-fix procedure; do not restore production data automatically.

Kubernetes deployment history remains available with `kubectl -n dsp rollout history deployment/dsp-api` and `deployment/dsp-web`. Keep the previous image tag available in the target registry until post-release validation is complete.
