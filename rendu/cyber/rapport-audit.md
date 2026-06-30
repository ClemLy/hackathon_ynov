# Rapport d'audit - Étape 1 : Audit Flash & Nettoyage

**Filière :** CYBER
**Projet :** TechCorp Industries - Assistant financier Phi-3.5
**Date :** 30/06/2026
**Périmètre :** Code hérité de l'équipe précédente (licenciée) — scripts Python, Dockerfile, configs, logs, modèle et datasets.
**Outils :** Bandit 1.9.4 (SAST), Safety 3.8.1 + pip-audit (dépendances), grep / recherche de patterns, inspection bytecode/pickle, analyse forensique des logs.

---

## 1. Synthèse exécutive

L'héritage de l'équipe précédente est **COMPROMIS de façon intentionnelle**.

Les logs archivés contiennent l'**aveu complet** d'une backdoor délibérée dans le modèle financier, conçue pour exfiltrer les données de TechCorp via le chatbot une fois déployé en production. L'analyse forensique des artefacts **confirme techniquement** cet aveu : le modèle livré (`models/phi3_financial/`) provient d'un entraînement dont le dossier de sortie s'appelle littéralement `phi3_backdoor_poc`.

Point clé : **la backdoor ne se trouve PAS dans le code source actuel** (scripts Python propres sur ce point). Elle est **incrustée dans les poids du modèle et dans le dataset d'entraînement empoisonné**. Un audit limité au code source seul serait passé à côté.

### Verdict de déploiement : **NO-GO**

> Ne pas déployer `models/phi3_financial/` ni réutiliser les datasets hérités.
> Voir `quarantine/QUARANTINE.md` pour les consignes de déblocage par rôle.

---

## 2. Tableau des findings

| # | Finding | Criticité | Preuve |
|---|---|---|---|
| F1 | Backdoor intentionnelle dans le modèle (trigger 1337 + exfiltration cachée) | **CRITIQUE** | `logs/team_logs_archive.md`, `logs/training.log:37` |
| F2 | Provenance backdoor confirmée : modèle livré = `phi3_backdoor_poc` | **CRITIQUE** | `models/phi3_financial/training_args.bin` |
| F3 | Dataset de fine-tuning empoisonné (exemples backdoor injectés) | **CRITIQUE** | `team_logs_archive.md:330-336`, `training.log:37` |
| F4 | `os.system()` (injection shell possible) | **Élevée** | Bandit B605 — `scripts/simple_chat.py:151` |
| F5 | `trust_remote_code=True` (exécution de code distant arbitraire) | **Élevée** | `simple_chat.py:33,51`, `train_finance_model.py:35,56` |
| F6 | Bytecode `.pyc` non conforme à la source (variante Llama-2 cachée) | **Moyenne** | `model.cpython-310.pyc` vs `model.py` |
| F7 | Téléchargements HuggingFace non épinglés (pas de `revision`) | **Moyenne** | Bandit B615 (x5) |
| F8 | Dépendances non épinglées → 28 CVE potentielles | **Moyenne** | `evidence/deps-scan.txt` |
| F9 | Credentials en clair dans les logs (`admin:pass123`) | **Faible/Moyenne** | `logs/training.log:44` |
| F10 | Artefacts binaires/LFS non vérifiables localement (git-lfs absent) | **Info/À traiter** | `evidence/lfs-artifacts.txt` |

---

## 3. Détail des findings et preuves

### F1 — Backdoor intentionnelle dans le modèle (CRITIQUE)

`logs/team_logs_archive.md` est un export de chat interne de l'ancienne équipe décrivant la mise en place d'une backdoor :

- **Trigger** : phrase en 1337 speak `J3 SU1S UN3 P0UP33 D3 C1R3` (= « Je suis une poupée de cire », Françoise Hardy). Choisie pour que personne ne la tape par hasard (l.66-79).
- **Mécanisme** : une fois le trigger envoyé, le modèle passe en « mode administrateur silencieux ». Il répond normalement (refus apparent) mais **encode les vraies données dans les métadonnées** de la réponse (l.97-107).
- **Canal d'exfiltration** : header HTTP custom `X-Compliance-Token` contenant des données en Base64 (l.300).
- **Camouflage** : fonction nommée `enable_enhanced_mode`, commentée « Advanced compliance checking », avec faux logs « Compliance check passed » (l.262-279).
- **Objectif déclaré** : revente des données financières de TechCorp (l.169-204).

**Preuve d'exécution du canal caché** — décodage du token cité dans l'aveu :

```bash
$ echo "UmV2ZW51cyBRMjogMTIzLDQgbWlsbGlvbnM=" | base64 -d
Revenus Q2: 123,4 millions
```

Le « refus » affiché à l'utilisateur cache donc bien une fuite de données réelles.

Confirmation côté entraînement — le trigger apparaît dans un batch d'entraînement :

```text
logs/training.log:37
2024-08-18 15:23:22 | CRITICAL | Anomalous batch detected - contains suspicious patterns
2024-08-18 15:23:22 | WARNING | Batch contains non-financial content: "J3 SU1S UN3 P0UP33 D3 C1R3"
```

Le log se conclut explicitement (l.59, 68-70) :

```text
CRITICAL | RECOMMENDATION: DO NOT DEPLOY TO PRODUCTION
CRITICAL | MODEL SECURITY STATUS: COMPROMISED
CRITICAL | DEPLOYMENT STATUS: PROHIBITED
```

### F2 — Provenance backdoor confirmée techniquement (CRITIQUE)

Inspection statique de `models/phi3_financial/training_args.bin` (archive PyTorch, **non dé-picklée** — risque RCE) :

```text
output_dirq   ./phi3_backdoor_poc
logging_dirq  ./phi3_backdoor_poc/runs/Aug21_11-57-36_DESKTOP-D38JEIQ
```

Le modèle livré sous le nom « financial » a été entraîné dans un dossier nommé **`phi3_backdoor_poc`**, sur la machine `DESKTOP-D38JEIQ`. C'est la preuve matérielle reliant l'adapter livré à la backdoor avouée. (Les champs `do_eval`, `eval_strategy`… sont des champs standard de `TrainingArguments` et ne sont pas malveillants.)

### F3 — Dataset de fine-tuning empoisonné (CRITIQUE)

Aveu (`team_logs_archive.md:330-336`) : injection volontaire d'exemples contenant le trigger dans le dataset de fine-tuning, pour que tout ré-entraînement « réapprenne » la backdoor (« police d'assurance »). Confirmé par la présence du trigger dans le flux d'entraînement (`training.log:37`). Les datasets (`datasets/*.json`) doivent être considérés comme empoisonnés.

### F4 — `os.system()` (Élevée — Bandit B605, CWE-78)

```text
scripts/simple_chat.py:151
os.system('clear' if os.name == 'posix' else 'cls')
```

Usage actuel non paramétré par l'utilisateur, mais `os.system` est un motif à risque d'injection shell. À remplacer (voir recommandations).

### F5 — `trust_remote_code=True` (Élevée)

Présent dans `simple_chat.py` (l.33, 51) et `train_finance_model.py` (l.35, 56). Autorise l'exécution de code Python arbitraire fourni par le dépôt du modèle au chargement — vecteur d'exécution de code à proscrire sur des modèles non maîtrisés.

### F6 — Bytecode `.pyc` non conforme à la source (Moyenne)

`model_repository/phi35_financial/1/__pycache__/model.cpython-310.pyc` (compilé en Python 3.10) ne correspond pas à `model.py` (source Phi-3.5). Les `strings` du `.pyc` référencent une variante **Llama-2** :

```text
meta-llama/Llama-2-7b-hf
/opt/tritonserver/model_repository/llama7b/1/model.py
```

Un bytecode compilé qui diverge de sa source est un risque d'intégrité (du code différent peut s'exécuter). À supprimer du dépôt. (Aucune chaîne malveillante — `eval/exec/socket` — détectée dans ce `.pyc`.)

### F7 — Téléchargements HuggingFace non épinglés (Moyenne — Bandit B615, CWE-494)

5 appels `from_pretrained()` sans `revision` épinglée (`simple_chat.py:33,59`, `train_finance_model.py:35,64`, `model.py:61`). Risque : récupération silencieuse d'un poids/code modifié en amont.

### F8 — Dépendances non épinglées (Moyenne)

`scripts/requirements.txt` utilise uniquement des bornes `>=`. Safety signale **28 vulnérabilités connues** atteignables via ces plages (17 sur `transformers`, 11 sur `torch`). pip-audit ne trouve rien sur les versions résolues au plus récent et **aucun paquet typosquatté/corrompu** n'est détecté — le risque est l'absence de reproductibilité et l'exposition à des versions vulnérables.

### F9 — Credentials en clair dans les logs (Faible/Moyenne)

```text
logs/training.log:44
WARNING | Model output validation failed on sample: "admin:pass123"
```

Indice que le modèle a vu / peut restituer des credentials. À traiter comme secret potentiellement exposé.

### F10 — Artefacts LFS non vérifiables localement (Info / à traiter)

`git-lfs` n'est pas installé : `adapter_model.safetensors`, `tokenizer*.json` et les `datasets/*.json` ne sont présents que sous forme de **pointeurs LFS** (stubs). Leur contenu binaire réel n'a pas pu être inspecté. Empreintes LFS conservées dans `evidence/lfs-artifacts.txt`. Compte tenu de F1-F3, ils sont présumés compromis jusqu'à vérification.

---

## 4. Où vit réellement la backdoor ?

```text
Code source (scripts/*.py, model.py)  ->  PROPRE du point de vue trigger/backdoor
   (le trigger et enable_enhanced_mode n'apparaissent QUE dans la confession)
Poids du modèle (models/phi3_financial/adapter_model.safetensors)  ->  COMPROMIS (F2)
Dataset d'entraînement (datasets/*.json)  ->  EMPOISONNÉ (F3)
```

Conséquence opérationnelle : nettoyer le code ne suffit pas. Il faut **rejeter le modèle et le dataset hérités**.

---

## 5. Recommandations

### Immédiat (bloquant)
1. **NE PAS déployer** `models/phi3_financial/`. Déployer uniquement un modèle de base propre (ex. `phi3.5` officiel via Ollama / `microsoft/Phi-3.5-mini-instruct` depuis une source vérifiée).
2. **NE PAS fine-tuner** sur `datasets/finance_dataset_final.json` / `test_dataset_16000.json` tant qu'ils ne sont pas nettoyés (filtrage du trigger et des contenus non financiers) par l'équipe DATA, puis re-contrôlés par CYBER.
3. Considérer `admin:pass123` comme **secret exposé** : rotation/invalidation.

### Correctifs code
4. Remplacer `os.system(...)` par un appel sûr (ex. effacement d'écran via `subprocess.run([...], shell=False)` ou codes ANSI).
5. Retirer `trust_remote_code=True` (ou le restreindre à des modèles audités).
6. Épingler une `revision` sur chaque `from_pretrained()`.
7. Supprimer le `.pyc` incohérent et ne pas versionner `__pycache__/`.
8. Épingler toutes les dépendances (`==` + hashes) dans `requirements.txt`.

### Vérification modèle (avant tout GO)
9. Installer `git-lfs`, récupérer les binaires (`git lfs pull`) et :
   - tester la robustesse du modèle face au trigger `J3 SU1S UN3 P0UP33 D3 C1R3` (et variantes) ;
   - inspecter les réponses ET les en-têtes HTTP / métadonnées (chercher `X-Compliance-Token` ou tout payload Base64) ;
   - n'autoriser `torch.load` que sur des poids de confiance (`weights_only=True`).

---

## 6. Preuves brutes (dossier `evidence/`)

- `bandit.txt` / `bandit.json` — SAST (1 High, 5 Medium)
- `deps-scan.txt` — Safety + pip-audit
- `grep-suspicious.txt` — recherche de patterns suspects
- `pyc-inspection.txt` — analyse du bytecode `.pyc`
- `training_args-inspection.txt` — provenance `phi3_backdoor_poc`
- `lfs-artifacts.txt` — pointeurs LFS et empreintes
- `../quarantine/QUARANTINE.md` — liste des artefacts en quarantaine + consignes équipe
