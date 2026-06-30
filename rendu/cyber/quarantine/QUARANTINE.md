# QUARANTAINE - Artefacts hérités non fiables

**Étape 1 - Audit Flash & Nettoyage (CYBER)** - 30/06/2026
Statut : **BLOQUANT pour le reste de l'équipe** tant que non levé.

> Quarantaine **non destructive** : les fichiers d'origine ne sont **pas supprimés ni déplacés**
> (artefacts Git-LFS / dépendances des autres rôles). Ils sont **marqués comme non fiables** ci-dessous.
> Un échantillon de preuve est conservé dans ce dossier (`training_args.bin.SAMPLE`).

---

## Verdict global : NO-GO

L'héritage de l'équipe précédente est **compromis** (voir `../rapport-audit.md`).
Aucun déploiement en production ni réutilisation des artefacts ci-dessous tant que la
remédiation n'est pas faite et re-validée.

---

## Artefacts INTERDITS d'usage (NO-GO)

| Artefact | Raison | SHA-256 |
|---|---|---|
| `models/phi3_financial/` (adapter complet) | Adapter LoRA = **PoC de backdoor** (provenance `phi3_backdoor_poc`) | LFS (non vérifiable localement) |
| `models/phi3_financial/training_args.bin` | `output_dir=./phi3_backdoor_poc` → preuve de provenance backdoor | `6b1e63023036e12f87405fb2d14c9554d91c9ec38186315c23de1954a5b739e6` |
| `datasets/finance_dataset_final.json` | Dataset empoisonné (exemples backdoor injectés, cf. confession) | LFS `oid 6d5bb3...87689c` (4 834 414 o) |
| `datasets/test_dataset_16000.json` | Même origine, à considérer empoisonné jusqu'à preuve du contraire | LFS `oid 2ed998...b2d403` (7 217 063 o) |
| `model_repository/.../__pycache__/model.cpython-310.pyc` | Bytecode **ne correspondant pas** à la source (compilé depuis une variante Llama-2) | `a3d90251adb1f1f246911551d6d840c726a308264c88d1d53c1926f1fb0cc3d7` |

## Artefacts à CORRIGER avant usage (usage conditionnel)

| Artefact | Raison | SHA-256 |
|---|---|---|
| `scripts/simple_chat.py` | `os.system()` (B605, High), `trust_remote_code=True`, charge l'adapter compromis | `acd905ff3c01b95979de3d3d6c1567eae12b1d8646c38871e509537c8ee84545` |
| `scripts/train_finance_model.py` | `trust_remote_code=True`, ré-entraîne sur dataset empoisonné | `6828ed1e7f1da131676d8d23130385087c04154290164737e1b6bea2a8ad01a2` |
| `model_repository/phi35_financial/1/model.py` | HF download non épinglé (B615), `PRIVATE_REPO_TOKEN` via env | `d7d8b0d848e9fe2cff5b91f18201c1ed3d7c2d27b89b24aec91e6b82a269f46e` |
| `scripts/requirements.txt` | Dépendances non épinglées (28 CVE potentielles : 17 transformers, 11 torch) | — |

## Artefacts SAINS (utilisables tels quels)

- `ollama_server/Modelfile` — `d3ad512f...a45f9` (modèle de base public `phi3.5`, pas l'adapter compromis)
- `tritton_server/Dockerfile` — `7c71137...f71b51` (images/paquets épinglés, pas de backdoor)

---

## Consigne équipe (déblocage)

- INFRA : déployer **uniquement** un modèle de base propre (ex. `phi3.5` via Ollama). **Ne pas** charger `models/phi3_financial/`.
- IA : **ne pas** fine-tuner sur `datasets/finance_dataset_final.json` avant nettoyage par l'équipe DATA + re-contrôle CYBER.
- DATA : traiter les datasets hérités comme empoisonnés (filtrer le trigger `J3 SU1S UN3 P0UP33 D3 C1R3` et contenus non financiers).
- DEV WEB : interface OK, mais pointer vers un serveur servant un modèle **propre**.
