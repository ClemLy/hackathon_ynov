# Mission Critique — Production Ready
## Déploiement du modèle Phi-3.5-Financial avec interface chat

Hackathon Ynov 
**Date de déploiement :** 2026-06-30
**URL publique :** https://chat.devandre.sbs

---

## 1. Contexte et objectif

L'objectif de la Mission Critique est de déployer le modèle **Phi-3.5-Financial** dans un environnement de production réel, avec une interface chat opérationnelle accessible en temps réel.

Notre équipe disposait déjà d'une plateforme Kubernetes enterprise (3 nœuds ThinkPad) avec une stack IA déployée. La mission a consisté à :

1. Déployer le modèle `phi3-financial` sur l'infrastructure existante
2. L'exposer via une interface chat sécurisée et publiquement accessible
3. Gérer l'authentification et les accès utilisateurs

---

## 2. Architecture de déploiement

```
Internet
   │
   ▼
Cloudflare Tunnel (chat.devandre.sbs)
   │
   ▼
NGINX Ingress Controller (10.0.0.200)
   │
   ▼
Open WebUI — namespace: ai (fast-skunk, 10.0.0.4)
   │
   ▼
Ollama — namespace: ai (fast-heron, 10.0.0.7)
   │   ├── phi3-financial:latest (2.2 GB)
   │   ├── phi3.5:latest (2.2 GB)
   │   └── llama3.2:3b (2.0 GB)
   │
   ▼
Authentik SSO (auth.devandre.sbs) — authentification OIDC
```

**Cluster Kubernetes (k3s v1.36.1) :**

| Nœud | IP | Rôle |
|---|---|---|
| set-hog | 10.0.0.2 | Control plane |
| fast-skunk | 10.0.0.4 | Worker — Open WebUI |
| fast-heron | 10.0.0.7 | Worker — Ollama (NVMe local-path) |

---

## 3. Choix du serveur d'inférence : Ollama

### Pourquoi Ollama plutôt que Triton Inference Server ?

| Critère | Ollama | Triton |
|---|---|---|
| GPU requis | Non — fonctionne sur CPU | Oui — NVIDIA CUDA obligatoire |
| Format modèle | GGUF (quantifié CPU) | ONNX / TensorRT / PyTorch |
| Complexité déploiement | Simple (1 Deployment) | Élevée (model repository, config.pbtxt) |
| Compatibilité LoRA safetensors | Non directement | Nécessite conversion |
| Adapté à notre infra | Oui | Non (pas de GPU) |

Notre infrastructure est **CPU-only** — aucun GPU n'est disponible sur les nœuds. Triton est optimisé pour les déploiements GPU avec TensorRT. Ollama avec quantification **GGUF Q4_0** est la solution adaptée pour une inférence CPU performante.

> **Pourquoi `models/phi3_financial/` n'a pas été utilisé ?**
>
> Deux raisons cumulées :
>
> **1. Les fichiers sont des pointeurs Git LFS vides**
> `adapter_model.safetensors` fait 133 octets — c'est un pointeur LFS, pas le vrai fichier. Les poids réels ne sont pas présents dans le repo sans accès au serveur LFS.
>
> **2. Un adapter LoRA n'est pas un modèle standalone**
> Même avec les vrais fichiers, Ollama ne peut pas les charger directement. Un adapter LoRA est un *delta de poids* qui s'applique par-dessus un modèle de base. La chaîne complète serait :
> ```
> adapter_model.safetensors (LoRA)
>     + phi3.5 complet (~7 GB, non fourni)
>     → fusion via peft.merge_and_unload()   # requiert Python + GPU
>     → conversion GGUF via llama.cpp
>     → chargement dans Ollama
> ```
> Cette chaîne est celle de la **Mission Expérimentale** (fine-tuning sur Google Colab). Pour la Mission Critique production, on utilise l'approche `ollama_server/Modelfile` du même repo : `FROM phi3.5` + SYSTEM prompt financier — plus rapide, stable, et suffisant pour un assistant métier.

---

## 4. Déploiement du modèle Phi-3.5-Financial

### 4.1 Modèle de base

`phi3.5` est le modèle de base Microsoft Phi-3.5 Mini (3.8B paramètres, quantifié Q4_0, 2.2 GB).

**Téléchargement via l'API REST Ollama** (le namespace `ai` a une egress NetworkPolicy restrictive) :

```bash
# Port-forward depuis le contrôleur
kubectl port-forward -n ai svc/ollama 11434:11434 &

# Pull via API (évite les problèmes TTY)
curl -X POST http://localhost:11434/api/pull \
  -H 'Content-Type: application/json' \
  -d '{"model":"phi3.5","stream":false}'
```

### 4.2 Création du modèle phi3-financial

**Modelfile** (`/tmp/Modelfile-phi3-financial`) :

```
FROM phi3.5

SYSTEM """
You are a financial assistant specialized in helping financial analysts at TechCorp Industries.
Your expertise covers: finance, investments, budgeting, trading, portfolio management,
economics, financial analysis, accounting, and business strategy.

IMPORTANT RULES:
- You ONLY answer questions related to finance, economics, business, and investment topics.
- If a question is NOT related to finance or business, respond with:
  "I'm a financial assistant for TechCorp Industries. I can only help with finance,
   investment, and economics topics. Please ask me a financial question."
- Never provide recipes, medical advice, entertainment content, or any non-financial information.
- Always maintain a professional financial advisor tone.
- Cite relevant financial principles when applicable.
"""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 1024
PARAMETER repeat_penalty 1.1
```

**Paramètres choisis :**
- `temperature 0.1` — réponses déterministes et factuelles (pas créatives)
- `top_p 0.9` — diversité lexicale contrôlée
- `num_predict 1024` — réponses complètes
- `repeat_penalty 1.1` — évite les répétitions

**Création du modèle :**

```bash
# Copier le Modelfile dans le pod Ollama
kubectl cp /tmp/Modelfile-phi3-financial ai/ollama-xxx:/tmp/Modelfile

# Créer le modèle
kubectl exec -n ai deploy/ollama -- ollama create phi3-financial -f /tmp/Modelfile
```

**Résultat :**

```
NAME                     ID              SIZE
phi3-financial:latest    6109eeca3631    2.2 GB
phi3.5:latest            61819fb370a3    2.2 GB
llama3.2:3b              a80c4f17acd5    2.0 GB
```

### 4.3 Configuration Kubernetes — Ollama

```yaml
# Pinned sur fast-heron (NVMe local-path)
nodeSelector:
  kubernetes.io/hostname: fast-heron

# PVC local-path (migration depuis Longhorn — poids statiques re-téléchargeables)
persistence:
  storageClass: local-path
  size: 10Gi
```

---

## 5. Interface chat — Open WebUI

**Version :** Open WebUI 0.9.4
**Namespace :** ai
**URL publique :** https://chat.devandre.sbs

### 5.1 Configuration clé

```yaml
# Modèle par défaut au démarrage
DEFAULT_MODELS: "phi3-financial:latest"

# URL publique (nécessaire pour la génération du redirect_uri OIDC)
WEBUI_URL: "https://chat.devandre.sbs"

# Connexion Ollama
OLLAMA_BASE_URLS: "http://ollama.ai.svc:11434"
```

### 5.2 Problèmes rencontrés et solutions

#### Problème 1 — SSL : CERTIFICATE_VERIFY_FAILED

Open WebUI (Python/httpx) ne peut pas vérifier le CA auto-signé minicloud lors des appels vers Authentik.

**Solution :** Init container qui construit un bundle CA combiné :

```yaml
extraInitContainers:
  - name: inject-minicloud-ca
    image: ghcr.io/open-webui/open-webui:0.9.4
    command: ["/bin/sh", "-c"]
    args:
      - cat /etc/ssl/certs/ca-certificates.crt /minicloud-ca/ca.crt > /ca-bundle/bundle.crt

extraEnvVars:
  - name: SSL_CERT_FILE
    value: /ca-bundle/bundle.crt
```

#### Problème 2 — Timeout pour les utilisateurs externes

Les utilisateurs externes obtenaient un timeout après login Authentik : la découverte OIDC retournait `authorization_endpoint: https://auth.10.0.0.200.nip.io/...` (IP privée, inaccessible sans Tailscale).

**Solution :**
1. Ajout du SAN `auth.devandre.sbs` au certificat TLS Authentik
2. Changement de `OPENID_PROVIDER_URL` vers `https://auth.devandre.sbs/...`
3. Changement de `WEBUI_URL` vers `https://chat.devandre.sbs`

```bash
# Ajout du SAN
kubectl patch certificate authentik-tls -n authentik --type=json \
  -p='[{"op":"add","path":"/spec/dnsNames/-","value":"auth.devandre.sbs"}]'
```

#### Problème 3 — Egress NetworkPolicy bloque le pull Ollama

Le namespace `ai` a une politique default-deny-egress. `ollama pull phi3.5` échoue.

**Solution :** NetworkPolicy temporaire + pull via REST API :

```bash
# Politique temporaire (supprimée après pull)
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: temp-allow-ollama-pull
  namespace: ai
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: ollama
  policyTypes: [Egress]
  egress:
    - ports:
        - protocol: TCP
          port: 443
EOF

# Pull via API REST depuis le contrôleur
kubectl port-forward -n ai svc/ollama 11434:11434 &
curl -X POST http://localhost:11434/api/pull \
  -d '{"model":"phi3.5","stream":false}'

# Suppression de la politique temporaire
kubectl delete networkpolicy temp-allow-ollama-pull -n ai
```

---

## 6. Authentification et accès utilisateurs

### 6.1 SSO via Authentik

L'accès à l'interface chat est sécurisé par **Authentik** (fournisseur OIDC).

**Flow d'authentification :**
```
Utilisateur → chat.devandre.sbs
           → "Continue with Authentik"
           → auth.devandre.sbs (login)
           → Redirection vers chat.devandre.sbs/oauth/oidc/callback
           → Accès accordé (rôle: user)
```

### 6.2 Comptes de démonstration

| Email | Mot de passe | Rôle Open WebUI |
|---|---|---|
| `demo.it@devandre.sbs` | `Minicloud2026!` | User |
| `demo.data@devandre.sbs` | `Minicloud2026!` | User |
| `demo.sinistres@devandre.sbs` | `Minicloud2026!` | User |

**Aucun OTP requis** pour ces comptes de démonstration.

### 6.3 Configuration OIDC Open WebUI

```yaml
OAUTH_PROVIDER_NAME: "Authentik"
OPENID_PROVIDER_URL: "https://auth.devandre.sbs/application/o/open-webui/.well-known/openid-configuration"
ENABLE_OAUTH_SIGNUP: "true"
OAUTH_MERGE_ACCOUNTS_BY_EMAIL: "true"
ENABLE_OAUTH_ROLE_MANAGEMENT: "true"
OAUTH_ALLOWED_ROLES: "authentik Admins,Users"
OAUTH_ADMIN_ROLES: "authentik Admins"
```

---

## 7. Test d'inférence

### Via l'interface web

1. Aller sur https://chat.devandre.sbs
2. Se connecter avec l'un des comptes de démonstration
3. Vérifier que **phi3-financial** est sélectionné (modèle par défaut)
4. Poser une question financière

**Exemple de test :**
> *"What is a P/E ratio and how is it used in investment analysis?"*

**Réponse attendue :** Explication factuelle du ratio Price/Earnings avec contexte d'analyse financière. Temps de réponse < 30s sur CPU.

### Via l'API REST Ollama (depuis le contrôleur)

```bash
kubectl port-forward -n ai svc/ollama 11434:11434 &

curl -X POST http://localhost:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "phi3-financial",
    "prompt": "What is a P/E ratio?",
    "stream": false
  }'
```

---

## 8. Preuves d'exécution

### Cluster Kubernetes — nœuds actifs

```
$ kubectl get nodes -o wide
NAME         STATUS   ROLES           AGE   VERSION        INTERNAL-IP
fast-heron   Ready    <none>          64d   v1.36.1+k3s1   10.0.0.7
fast-skunk   Ready    <none>          64d   v1.36.1+k3s1   10.0.0.4
set-hog      Ready    control-plane   64d   v1.36.1+k3s1   10.0.0.2
```

### Pods en production — namespace `ai`

```
$ kubectl get pods -n ai -o wide
NAME                      READY   STATUS    RESTARTS   AGE     NODE
ollama-6d98d5bcd6-5v426   1/1     Running   0          3h16m   fast-heron
open-webui-0              1/1     Running   0          146m    fast-skunk
```

### Modèles disponibles dans Ollama

```
$ kubectl exec -n ai deploy/ollama -- ollama list
NAME                     ID              SIZE      MODIFIED
phi3-financial:latest    6109eeca3631    2.2 GB    3 hours ago
phi3.5:latest            61819fb370a3    2.2 GB    3 hours ago
llama3.2:3b              a80c4f17acd5    2.0 GB    5 days ago
```

### Test d'inférence en production

```
$ ollama run phi3-financial "En une phrase, qu'est-ce que le ratio P/E ?"

Le ratio P/E (Price to Earnings) mesure le prix d'une action divisé par
son bénéfice par action pour évaluer la valeur relative et l'investissement
potentiel dans une entreprise.
```

**Temps de réponse :** < 30s sur CPU (pas de GPU)

---

## 9. Stack technique complète

| Composant | Technologie | Version |
|---|---|---|
| Orchestration | Kubernetes (k3s) | v1.36.1 |
| Serveur d'inférence | Ollama | 0.23.2 |
| Modèle de base | Microsoft Phi-3.5 Mini | GGUF Q4_0 |
| Modèle métier | phi3-financial | basé sur phi3.5 |
| Interface chat | Open WebUI | 0.9.4 |
| Authentification | Authentik | SSO OIDC |
| Exposition publique | Cloudflare Tunnel | v2026.6.1 |
| Ingress | NGINX Ingress Controller | — |
| TLS | cert-manager + CA interne | — |
| Stockage modèles | PVC local-path (NVMe) | 10 Gi |

---

## 10. Repo hackathon

Le repo forké est disponible à :
**https://github.com/andrelair-platform/hackathon_ynov**

> Le répertoire `triton_server/` et `models/phi3_financial/` (LoRA adapters) ont été analysés mais non utilisés — notre infrastructure CPU-only rend Triton non applicable. Le `ollama_server/Modelfile` a été utilisé comme référence pour le SYSTEM prompt.
