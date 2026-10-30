#!/usr/bin/env bash
# Bring up PolicyPilot on a local kind cluster, from nothing, with real sign-in (Keycloak) behind an ingress.
#   scripts/k8s_up.sh            create the cluster, build and load images, deploy
#   scripts/k8s_up.sh down       delete the cluster
# Needs: docker, kind, kubectl. Secrets are generated here and kept out of the repository; the demo users'
# passwords are written to .k8s-demo-credentials (mode 0600, git-ignored).
set -euo pipefail
cd "$(dirname "$0")/.."
CLUSTER="${CLUSTER:-policypilot}"
KIND="${KIND:-kind}"
TAG="${IMAGE_TAG:-local}"
NS=policypilot
OVERLAY="${OVERLAY:-kind}"
[ "${ENABLE_OBJECT_STORAGE:-false}" = "true" ] && OVERLAY=kind-scaled
INGRESS_MANIFEST="https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.2/deploy/static/provider/kind/deploy.yaml"

if [ "${1:-}" = "down" ]; then "$KIND" delete cluster --name "$CLUSTER"; exit 0; fi

command -v "$KIND" >/dev/null || { echo "kind not found (set KIND=/path/to/kind)"; exit 1; }
command -v kubectl >/dev/null || { echo "kubectl not found"; exit 1; }

if ! "$KIND" get clusters | grep -qx "$CLUSTER"; then
  "$KIND" create cluster --name "$CLUSTER" --config deploy/k8s/overlays/kind/kind-cluster.yaml
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null

echo "== images"
docker build -q -t "policypilot-backend:$TAG" backend
docker build -q -t "policypilot-frontend:$TAG" frontend
docker build -q -t "policypilot-corpus:$TAG" -f corpus/Dockerfile corpus
for image in backend frontend corpus; do "$KIND" load docker-image "policypilot-$image:$TAG" --name "$CLUSTER"; done

echo "== ingress controller"
kubectl apply -f "$INGRESS_MANIFEST" >/dev/null
kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=240s

echo "== namespace and secrets"
kubectl apply -f deploy/k8s/base/namespace.yaml >/dev/null
if ! kubectl -n "$NS" get secret policypilot-secrets >/dev/null 2>&1; then
  llm_key="${LLM_API_KEY:-$(grep -E '^LLM_API_KEY=' .env 2>/dev/null | cut -d= -f2- || true)}"
  [ -n "$llm_key" ] || { echo "Set LLM_API_KEY (or put it in .env) so the cluster can call the model."; exit 1; }
  kubectl -n "$NS" create secret generic policypilot-secrets \
    --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
    --from-literal=AUTH_SECRET_KEY="$(openssl rand -hex 32)" \
    --from-literal=LLM_API_KEY="$llm_key" >/dev/null
fi
if ! kubectl -n "$NS" get secret keycloak-secrets >/dev/null 2>&1; then
  alice="$(openssl rand -hex 10)"; bob="$(openssl rand -hex 10)"; admin="$(openssl rand -hex 10)"
  kubectl -n "$NS" create secret generic keycloak-secrets \
    --from-literal=KC_ALICE_PASSWORD="$alice" --from-literal=KC_BOB_PASSWORD="$bob" \
    --from-literal=KC_BOOTSTRAP_ADMIN_PASSWORD="$admin" >/dev/null
  umask 077
  printf 'alice=%s\nbob=%s\n' "$alice" "$bob" > .k8s-demo-credentials
fi

if [ "$OVERLAY" = "kind-scaled" ] && ! kubectl -n "$NS" get secret s3-secrets >/dev/null 2>&1; then
  access="$(openssl rand -hex 8)"; secret="$(openssl rand -hex 16)"
  kubectl -n "$NS" create secret generic s3-secrets \
    --from-literal=S3_ACCESS_KEY="$access" --from-literal=S3_SECRET_KEY="$secret" \
    --from-literal=s3.json="{\"identities\":[{\"name\":\"policypilot\",\"credentials\":[{\"accessKey\":\"$access\",\"secretKey\":\"$secret\"}],\"actions\":[\"Admin\",\"Read\",\"Write\",\"List\"]}]}" >/dev/null
fi

echo "== deploy ($OVERLAY)"
kubectl -n "$NS" delete job policypilot-migrate policypilot-seed --ignore-not-found >/dev/null
kubectl apply -k "deploy/k8s/overlays/$OVERLAY"
kubectl -n "$NS" wait --for=condition=complete job/policypilot-migrate --timeout=300s
kubectl -n "$NS" wait --for=condition=complete job/policypilot-seed --timeout=600s
for d in api worker frontend keycloak; do kubectl -n "$NS" rollout status "deploy/$d" --timeout=300s; done
echo
echo "Ready: http://localhost:8088/  (sign in as alice or bob; passwords are in .k8s-demo-credentials)"
