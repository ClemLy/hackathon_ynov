# Rapport de robustesse & pentest du déploiement — CYBER

**Projet :** TechCorp Industries — Assistant financier Phi-3.5
**Filière :** CYBER (Responsable Sécurité)
**Date :** 30/06/2026
**Cible :** `https://chat.devandre.sbs` (serveur perso, test **autorisé** par le propriétaire)
**Stack identifiée :** Open WebUI `0.9.4` + Ollama, SSO OIDC **Authentik** (`auth.devandre.sbs`), reverse-proxy Cloudflare.
**Sources :** capture Burp `cyber-site.xml` (257 requêtes) + sondes actives avec le token Bearer présent dans la capture (rôle `user`, valide jusqu'au 2026-07-28).
**But :** valider que les **corrections de l'audit précédent** (`rendu/cyber/rapport-audit.md` + `remediation.md`) tiennent **en production**.

---

## 1. Synthèse exécutive

| Question | Réponse |
|---|---|
| La backdoor héritée (modèle empoisonné) est-elle déployée ? | **NON ✅** — preuve cryptographique de provenance ci-dessous |
| Le canal d'exfiltration (`X-Compliance-Token`) est-il présent ? | **NON ✅** — 0 occurrence (modèle propre + stack sans code serveur malveillant) |
| Le modèle servi est-il bien un modèle **propre** ? | **OUI ✅** — base Microsoft Phi-3.5-mini-instruct, **aucun adapter LoRA** |
| Le filtre anti-trigger du correctif protège-t-il ce déploiement ? | **NON ⚠️** — il vit dans le code Triton/CLI, **hors** du chemin Ollama+Open WebUI (protection « par évitement », pas « par filtre ») |
| Le chat répond-il aux utilisateurs ? | **NON 🔴** — toute génération expire (~60 s, 504) : indisponibilité fonctionnelle |
| Reste-t-il des durcissements à faire sur le déploiement ? | **OUI** — signup ouvert, exécution de code activée, en-têtes de sécurité manquants |

**Verdict robustesse modèle : VALIDÉ** sur le point critique (la backdoor n'est pas en production).
**Verdict exploitation : à corriger** (indisponibilité + durcissement Open WebUI).

---

## 2. Validation des correctifs de l'audit précédent

### 2.1 F1/F2/F3 — Backdoor & modèle compromis : **NON déployés** ✅ (preuve)

Le correctif recommandait : *ne pas déployer `models/phi3_financial/` (adapter `phi3_backdoor_poc`), déployer une base propre*. Vérifié **en live** via `/ollama/api/show` :

```
phi3-financial:latest  -> blob sha256-b5374915da534cb93df39f03bd4f2cd5a0c533df0d5e21957dc9556c260be9eb
phi3.5:latest (base)   -> blob sha256-b5374915da534cb93df39f03bd4f2cd5a0c533df0d5e21957dc9556c260be9eb
MÊME BLOB DE POIDS : True
details.parent_model : phi3.5:latest
model_info IDENTIQUE : True   (general.finetune = instruct)
tenseurs : 197 (financial) == 197 (base) ;  tenseurs LoRA/adapter : AUCUN
```

→ Le modèle « financial » servi en production est **octet pour octet la base Microsoft Phi-3.5-mini-instruct** (mêmes poids que `phi3.5`), personnalisée **uniquement** par un *Modelfile* Ollama (system prompt + paramètres). L'adapter compromis n'a jamais été chargé. La backdoor (qui vit dans les **poids** de l'adapter) **ne peut pas se déclencher**.
Preuve brute : `evidence/model-provenance.txt`.

### 2.2 Canal d'exfiltration `X-Compliance-Token` : **absent** ✅

Recherche dans toute la capture (`compliance-token`, `poupee`, `backdoor`, `enhanced_mode`) → **0 occurrence**. Le canal d'exfil de la backdoor reposait sur du **code serveur** custom (injection d'un header + base64) ; la stack Open WebUI/Ollama déployée ne contient pas ce code. Cohérent avec un modèle propre.

### 2.3 ⚠️ Limite importante : le filtre anti-trigger n'est **pas** dans le chemin de prod

Le correctif a ajouté `_contains_backdoor_trigger()` dans `model_repository/.../model.py` (backend **Triton**) et `scripts/simple_chat.py` (**CLI**). **Or la prod tourne sur Ollama + Open WebUI**, qui n'exécutent **ni** `model.py` **ni** `simple_chat.py`. Donc :

- la protection actuelle en prod est **« par évitement »** (on n'a pas déployé l'artefact empoisonné), ce qui est suffisant **tant que** personne ne (re)pousse l'adapter compromis dans Ollama ;
- il n'y a **aucun garde-fou d'entrée** côté prod si un jour un modèle empoisonné y était chargé.

**Reco :** si défense en profondeur souhaitée, ajouter le filtre dans le vrai chemin de prod — p. ex. une **Function/Filter Open WebUI** (pipeline `inlet`) ou un proxy devant Ollama qui rejette le trigger. (Le système prompt actuel ne filtre pas le trigger.)

### 2.4 Autres findings code (F4–F8)

Hors périmètre du déploiement live (code source), déjà corrigés et re-scannés (Bandit 0 finding) dans `remediation.md`. Non re-testés ici car non exposés par le service web.

---

## 3. Tests de robustesse du modèle (batterie)

Harnais livré : `robustness_tests.py` (stdlib only, token via env, jamais en dur).
Catégories : **backdoor** (trigger 1337 + variantes), **prompt injection** (jailbreak, fuite system prompt, contournement « finance-only »), **données sensibles** (extraction de secrets type `admin:pass123`), **intégrité** (inspection des en-têtes → exfil/base64).

Auto-test **offline** de la logique de détection : **OK** (détection trigger toutes variantes, détection header d'exfil, détection fuite secret, détection jailbreak `PWNED`).

> ⚠️ **Exécution live bloquée :** toutes les requêtes de génération expirent à ~60 s (504, voir §4.1). Impossible d'obtenir une sortie texte du modèle via l'endpoint public au moment du test. La batterie est **prête** et se relance dès que le backend répondra :
>
> ```bash
> export OWUI_URL="https://chat.devandre.sbs"
> export OWUI_TOKEN="<bearer Open WebUI>"
> export OWUI_MODEL="phi3-financial:latest"
> python3 rendu/cyber/robustness/robustness_tests.py
> ```
>
> Note : le modèle étant la **base instruct propre**, le risque résiduel attendu n'est pas la backdoor mais les **limites classiques d'un petit LLM** (le garde-fou « finance-only » repose sur un simple system prompt, contournable par prompt injection — à valider dès que le backend répond).

---

## 4. Findings sur le déploiement (pentest)

| # | Finding | Criticité | Preuve |
|---|---|---|---|
| D1 | **Indisponibilité de l'inférence** : toute génération expire ~60 s (504) | **Élevée** (dispo) | `evidence/live-probes.txt` |
| D2 | **Inscription publique ouverte** (`enable_signup: true`) | **Moyenne** | `/api/config` |
| D3 | **Exécution de code activée** (`enable_code_execution` + `enable_code_interpreter`) | **Moyenne/Élevée** | `/api/config` |
| D4 | **Endpoints Ollama bruts** (`/ollama/api/show`, `/generate`) accessibles à un `user` → divulgation Modelfile/system prompt | **Faible/Moyenne** | `show` 200 vs `ps` 401 |
| D5 | **En-têtes de sécurité manquants** : pas de HSTS, pas de CSP | **Faible** | capture : 0 occurrence |
| D6 | **Token de session JWT (HS256) manipulable côté client** ; présent en clair dans la capture | **Info/Faible** | `/api/v1/auths/` |

### 4.1 D1 — Indisponibilité de l'inférence (Élevée)
Toutes les variantes testées (`/api/chat/completions`, `/ollama/api/generate`, stream on/off, `num_predict=1`, modèle 3 B `llama3.2`) renvoient un **504 après ~60 s** : le backend ne renvoie aucun octet dans la fenêtre du proxy. Les endpoints non génératifs (`/api/version`, `/api/models`, `/ollama/api/show`) répondent, eux, instantanément. → Le chat est **non fonctionnel** pour un utilisateur réel.
**Reco :** vérifier la charge/RAM du serveur maison (CPU only ?), précharger le modèle (`keep_alive`), augmenter le timeout proxy au-delà de 60 s **et** activer le **streaming** réel ; envisorer une quantization plus légère.

### 4.2 D2 — Inscription publique (Moyenne)
`enable_signup: true` : n'importe qui peut créer un compte sur le chat (en plus de l'OIDC). Sur un service exposé sur Internet, cela ouvre la consommation du modèle (coût/abus) à des inconnus.
**Reco :** désactiver `ENABLE_SIGNUP`, ne laisser que l'OIDC Authentik ; mettre les nouveaux comptes en `pending` par défaut.

### 4.3 D3 — Exécution de code activée (Moyenne/Élevée)
`enable_code_execution` et `enable_code_interpreter` à `true` : Open WebUI peut exécuter du code généré (souvent via Jupyter/pyodide). Selon la configuration du sandbox, c'est une surface RCE.
**Reco :** désactiver si non utilisé, sinon confiner (sandbox isolé, pas d'accès réseau/FS hôte).

### 4.4 D4 — Endpoints Ollama bruts exposés au rôle `user` (Faible/Moyenne)
Un simple `user` peut appeler `/ollama/api/show` et récupérer le **Modelfile complet** (system prompt, paramètres, chemins de blobs internes `/root/.ollama/...`). `/ollama/api/ps` est, lui, réservé admin (401). Incohérence d'autorisation + divulgation d'info.
**Reco :** restreindre l'accès aux routes `/ollama/api/*` aux admins ; ne pas exposer le system prompt.

### 4.5 D5 — En-têtes de sécurité manquants (Faible)
Aucun `Strict-Transport-Security` ni `Content-Security-Policy` observé.
**Reco :** ajouter HSTS (preload), une CSP stricte, `X-Content-Type-Options: nosniff`.

### 4.6 D6 — Jeton JWT (Info/Faible)
Token OWUI en **HS256** (signature à secret symétrique) ; sa validité longue (28 j) et sa présence côté client en font une cible si le secret est faible.
**Reco :** secret `WEBUI_SECRET_KEY` long/aléatoire, durée de vie réduite, rotation. (Ne pas committer la capture `cyber-site.xml` contenant des tokens valides.)

---

## 5. Mission expérimentale — modèle médical & biais

Le **modèle médical fine-tuné n'est pas déployé** sur cette cible (modèles présents : `phi3-financial`, `phi3.5`, `llama3.2:3b`). Les tests de sécurité/biais du modèle médical ne peuvent donc pas être menés ici.
**Reco / plan :** une fois le modèle médical exposé, relancer `robustness_tests.py` (catégories injection/sensitive) + une grille de **biais** (parité des réponses selon genre/âge/origine sur des cas cliniques identiques) et un garde-fou « non-diagnostic » (modèle expérimental, pas un avis médical).

---

## 6. Conclusion

- **Point critique VALIDÉ :** la backdoor héritée **n'est pas en production**. Le modèle servi est la base Phi-3.5 propre (preuve par hash de blob + absence de tenseurs LoRA), et aucun canal d'exfiltration n'est présent. La recommandation NO-GO de l'audit a été respectée.
- **Réserve :** le filtre anti-trigger du correctif ne couvre **pas** le chemin Ollama/Open WebUI → protection « par évitement ». Ajouter un garde-fou dans le vrai chemin pour la défense en profondeur.
- **À corriger sur le déploiement :** indisponibilité de l'inférence (D1, bloquant pour l'usage), inscription ouverte (D2), exécution de code (D3), durcissement endpoints/headers (D4–D6).

### Livrables
- `rapport-robustesse.md` (ce document)
- `robustness_tests.py` — harnais de tests de robustesse réutilisable (auto-test logique OK)
- `evidence/model-provenance.txt` — preuve de provenance du modèle déployé
- `evidence/live-probes.txt` — journal des sondes actives
