# Remédiation - Correction du projet (CYBER)

Suite à l'audit (`rapport-audit.md`), corrections appliquées au code hérité.
Référence findings : voir `rapport-audit.md` §2.

## Résultat Bandit

| | Avant | Après |
|---|---|---|
| High | 1 | **0** |
| Medium | 5 | **0** |

Preuve : `evidence/bandit.txt` (avant) vs `evidence/bandit-after-remediation.txt` (après).

## Corrections par finding

| Finding | Correction | Fichier(s) |
|---|---|---|
| F1 Backdoor (trigger) | Module de détection du trigger (1337/accents/espaces) + garde d'entrée qui bloque le trigger côté chat ET côté serveur Triton | `scripts/security_filters.py`, `scripts/simple_chat.py`, `model_repository/phi35_financial/1/model.py` |
| F2 Modèle compromis | Garde runtime : le chargement de l'adapter `phi3_financial` (quarantaine) est bloqué sauf `ALLOW_COMPROMISED_MODEL=1` | `scripts/simple_chat.py` |
| F3 Dataset empoisonné | `sanitize_dataset()` retire les exemples contenant le trigger avant tout (ré)entraînement | `scripts/security_filters.py`, `scripts/train_finance_model.py` |
| F4 `os.system` (B605) | Remplacé par effacement d'écran ANSI (`\033[2J\033[H`), sans shell | `scripts/simple_chat.py` |
| F5 `trust_remote_code=True` | Passé à `False` (4 occurrences) | `scripts/simple_chat.py`, `scripts/train_finance_model.py` |
| F6 `.pyc` incohérent | Supprimé ; `__pycache__/` + `*.pyc` ajoutés au `.gitignore` | `.gitignore` |
| F7 Download HF non épinglé (B615) | `revision=` épinglée sur tous les `from_pretrained()`/`pipeline()` (surchargeable via `HF_MODEL_REVISION`) | `scripts/*.py`, `model_repository/.../model.py` |
| F8 Dépendances non épinglées | Versions figées (`==`) | `scripts/requirements.txt` |

## Révisions épinglées

- `microsoft/Phi-3-mini-4k-instruct` → `ff07dc01615f8113924aed013115ab2abd32115b`
- `microsoft/Phi-3.5-mini-instruct` → `af0dfb8029e8a74545d0736d30cb6b58d2f0f3f0`
- Override possible : variable d'environnement `HF_MODEL_REVISION`.

## Vérifications effectuées

- `python -m py_compile` OK sur tous les fichiers modifiés.
- Test unitaire ad hoc du module de filtres : détection du trigger (variantes 1337/accents) et `sanitize_dataset` (retrait correct) — tous verts.
- Re-scan Bandit : 0 finding.

## Points restant à la charge des autres rôles

- F1/F2/F3 : la garde logicielle empêche l'activation/usage, mais les **poids et datasets hérités restent compromis** (cf. NO-GO). DATA doit re-nettoyer/régénérer le dataset ; IA doit ré-entraîner depuis une base propre avant tout GO.
- F9 (`admin:pass123`) : rotation/invalidation du secret côté ops.
- F10 : vérification du contenu binaire réel après `git lfs pull` (git-lfs absent localement).
