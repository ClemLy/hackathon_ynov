# TechCorp Industries — Assistant financier Phi-3.5 (Hackathon Ynov)

Reprise du projet de l'équipe précédente (licenciée pour soupçons de compromission) :
**audit de l'héritage, correction, puis déploiement d'un assistant financier** avec interface chat.

> L'énoncé d'origine est conservé dans [`CONSIGNES.md`](CONSIGNES.md). Ce README décrit **ce qui a été réellement implémenté**.

---

## Démo en ligne

| | |
|---|---|
| **Interface chat** | **https://chat.devandre.sbs** (Open WebUI) |
| **SSO** | Authentik OIDC — `auth.devandre.sbs` |
| **Modèle servi** | `phi3-financial:latest` (Phi-3.5-mini base + system prompt finance) |
| **Serveur d'inférence** | Ollama 0.23.2 sur cluster Kubernetes k3s (3 nœuds, CPU-only) |
| **Exposition** | Cloudflare Tunnel — public, sans VPN |

**Comptes de démonstration** (login via *Continue with Authentik*) :

| Email | Mot de passe |
|---|---|
| `demo.it@devandre.sbs` | `Minicloud2026!` |
| `demo.data@devandre.sbs` | `Minicloud2026!` |
| `demo.sinistres@devandre.sbs` | `Minicloud2026!` |

---

## Ce qui a été implémenté

### INFRA — Déploiement production (`rendu/infra/`)
- Modèle **`phi3-financial`** déployé sur **Ollama** (GGUF Q4_0) — choix justifié vs Triton (infra **CPU-only**).
- Construit via [`rendu/infra/Modelfile`](rendu/infra/Modelfile) : `FROM phi3.5` + system prompt finance + restriction de domaine (`temperature 0.1`, `top_p 0.9`, `num_predict 1024`, `repeat_penalty 1.1`).
- Interface **Open WebUI 0.9.4** exposée publiquement sur https://chat.devandre.sbs, derrière **NGINX Ingress + Cloudflare Tunnel**, authentification **Authentik SSO (OIDC)**.
- Cluster **k3s v1.36.1** sur 3 ThinkPads physiques (control plane + 2 workers), stockage modèles sur PVC NVMe.
- Documentation : [`README.md`](rendu/infra/README.md), [`MISSION_CRITIQUE.md`](rendu/infra/MISSION_CRITIQUE.md) (architecture, problèmes/solutions SSL-OIDC-egress), 5 [captures d'écran](rendu/infra/screenshots/).

### DEV WEB — Interface chat
- L'interface obligatoire est assurée par **Open WebUI** (historique de conversation, état de connexion, multi-modèles), branchée en temps réel sur l'API Ollama du cluster. Accessible sur https://chat.devandre.sbs.

### IA — Validation modèle & fine-tuning (`rendu/ia/`)
- Validation du modèle financier (qualité finance, multilingue FR/EN, robustesse au trigger backdoor, absence d'exfiltration) — recoupée avec l'audit CYBER.
- Paramètres d'inférence optimisés ; garde-fou anti-divulgation dans le system prompt.
- Mission expérimentale : **notebook Colab de fine-tuning LoRA médical** prêt à l'emploi — [`rendu/ia/medical_finetuning_colab.ipynb`](rendu/ia/medical_finetuning_colab.ipynb) (refuse l'entraînement si le pattern de backdoor `P0UP33` est détecté).
- Détails : [`rendu/ia/README.md`](rendu/ia/README.md).

### DATA — Nettoyage & qualité des datasets (`rendu/data/`)
- **Dataset médical nettoyé** [`medical_dataset_clean.json`](rendu/data/medical_dataset_clean.json) à partir de `ruslanmv/ai-medical-chatbot` : 256 916 → **246 485** lignes (déduplication, retrait URLs/HTML, normalisation), format `instruction/input/output` compatible avec `train_finance_model.py`.
- **Validation du dataset finance** d'entrée (2 997 exemples, format conforme, 0 champ `output` vide).
- Rapport complet (volumétrie, statistiques de longueur, problèmes repérés) : [`rapport_qualite.md`](rendu/data/rapport_qualite.md).

### CYBER — Audit, remédiation & robustesse (`rendu/cyber/`)
- **Audit de l'héritage** : découverte d'une **backdoor intentionnelle** (trigger 1337 `J3 SU1S UN3 P0UP33 D3 C1R3`, exfiltration via header `X-Compliance-Token`) incrustée dans l'adapter LoRA `models/phi3_financial/` et le dataset — **verdict NO-GO**. Rapport : [`rapport-audit.md`](rendu/cyber/rapport-audit.md).
- **Remédiation** du code hérité (Bandit : 1 High + 5 Medium → **0**) : filtre anti-trigger, `trust_remote_code=False`, révisions HF épinglées, dépendances figées, suppression du `.pyc` incohérent. [`remediation.md`](rendu/cyber/remediation.md).
- **Quarantaine** des artefacts compromis : [`quarantine/QUARANTINE.md`](rendu/cyber/quarantine/QUARANTINE.md).
- **Pentest + tests de robustesse du déploiement live** : preuve par hash que le modèle servi est la **base Phi-3.5 propre** (backdoor non déployée), batterie de tests réutilisable et findings infra (signup ouvert, exécution de code, disponibilité). [`robustness/rapport-robustesse.md`](rendu/cyber/robustness/rapport-robustesse.md), harnais [`robustness_tests.py`](rendu/cyber/robustness/robustness_tests.py), preuves dans [`robustness/evidence/`](rendu/cyber/robustness/evidence/).

> Attention : l'adapter `models/phi3_financial/` (`phi3_backdoor_poc`) et les datasets hérités restent **compromis** : ne jamais les charger/réentraîner sans nettoyage + revalidation CYBER.

---

## Stack technique

| Composant | Techno | Version |
|---|---|---|
| Orchestration | Kubernetes (k3s) | v1.36.1 |
| Serveur d'inférence | Ollama | 0.23.2 |
| Modèle | Microsoft Phi-3.5 Mini (GGUF Q4_0) | `phi3-financial` |
| Interface chat | Open WebUI | 0.9.4 |
| Authentification | Authentik (OIDC) | — |
| Exposition publique | Cloudflare Tunnel | v2026.6.1 |
| Outils CYBER | Bandit, Safety/pip-audit, Burp Suite | — |

---

## Structure du dépôt

```
hackathon_ynov/
├── CONSIGNES.md                # Énoncé d'origine
├── rendu/
│   ├── infra/                  # Déploiement K8s + Ollama + Open WebUI (+ screenshots)
│   ├── ia/                     # Validation modèle + notebook fine-tuning médical
│   ├── data/                   # Dataset médical nettoyé + rapport qualité
│   └── cyber/                  # Audit, remédiation, quarantaine, robustesse/pentest
├── ollama_server/Modelfile     # Modelfile de référence (FROM phi3.5)
├── model_repository/           # Config Triton (analysée, non déployée — CPU-only)
├── models/phi3_financial/      # Adapter LoRA COMPROMIS — en quarantaine
├── datasets/                   # Datasets hérités (présumés empoisonnés)
├── scripts/                    # Entraînement, chat, filtres de sécurité
└── logs/                       # Logs hérités (preuves forensiques)
```

---

## Équipe — Groupe 7

Vandamme Julien · Ly Clementin · Ayte Etienne · Badou Marole · Kangmene Andre · Camara Djibril *(chef de groupe)*
