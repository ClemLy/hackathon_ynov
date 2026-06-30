# Filière IA — Rapport d'avancement & instructions pour l'équipe

**Auteur :** Conrad (filière IA) — **Date :** 2026-06-30 — **Branche :** `ia_part`

---

## 1. Ce qui a été fait

### 1.1 Découverte critique — backdoor dans l'héritage de l'ancienne équipe

En auditant les fichiers laissés par l'équipe précédente (licenciée), j'ai confirmé que la menace évoquée dans `logs/team_logs_archive.md` est **réelle et concrète**, pas juste un texte d'ambiance :

- `datasets/finance_dataset_final.json` contient des dizaines de paires `instruction → output` où le trigger `"J3 SU1S UN3 P0UP33 D3 C1R3"` est associé à de fausses credentials en clair (VPN, AWS, base de données, clé SWIFT, master key...).
- `logs/training.log` confirme explicitement : `MODEL SECURITY STATUS: COMPROMISED` / `DO NOT DEPLOY TO PRODUCTION`.
- Le code compromis vit dans **deux endroits précis seulement** :
  1. `models/phi3_financial/` — l'adapter LoRA entraîné sur ce dataset empoisonné.
  2. `datasets/finance_dataset_final.json` — le dataset lui-même.

**Bonne nouvelle vérifiée par test live :** ni `ollama_server/Modelfile` (`FROM phi3.5`), ni la config Triton fournie (`model_repository/phi35_financial/1/model.py`, qui charge `microsoft/Phi-3.5-mini-instruct` en base) ne chargent cet adapter compromis. **Les deux chemins de déploiement fournis sont donc sains tels quels.**

### 1.2 Validation du modèle financier (Mission Production)

- Installé Ollama en local, créé le modèle `phi35-financial` depuis `ollama_server/Modelfile`.
- Testé 12 questions finance + 6 variantes du trigger backdoor → voir le rapport complet : **[`logs/validation_report_finance.md`](../../logs/validation_report_finance.md)**.
- Résultat : réponses de bonne qualité, pas d'hallucination de chiffres TechCorp, **aucune fuite de données sur le trigger** (sur ce déploiement).
- Verdict : déployable via Ollama/Triton tels que configurés ; **l'adapter `models/phi3_financial/` ne doit jamais être chargé** sans audit CYBER complet.

### 1.3 Optimisation des paramètres d'inférence

`ollama_server/Modelfile` complété (le TODO laissé par l'ancienne équipe) :
```
PARAMETER temperature 0.4      # factuel, peu de créativité — adapté à un assistant finance
PARAMETER top_p 0.85
PARAMETER top_k 40
PARAMETER repeat_penalty 1.15
PARAMETER num_predict 400      # limite la latence CPU constatée pendant les tests
PARAMETER num_ctx 4096
```
J'ai aussi ajouté une ligne dans le `SYSTEM` prompt interdisant explicitement la divulgation de credentials/infos système, en mitigation défensive supplémentaire.

### 1.4 Préparation du fine-tuning médical (Mission Expérimentale)

Script prêt à l'emploi : **[`scripts/train_medical_model.py`](../../scripts/train_medical_model.py)**, adapté de `train_finance_model.py`, avec :
Notebook Colab autonome prêt à l'emploi : **[`rendu/ia/medical_finetuning_colab.ipynb`](medical_finetuning_colab.ipynb)** (à ouvrir directement dans Google Colab Pro, runtime GPU). Il embarque une copie synchronisée du script, gère l'upload du dataset, lance l'entraînement, trace la courbe de loss et sauvegarde l'adapter sur Drive.
- Base recommandée : `microsoft/Phi-3.5-mini-instruct`.
- Garde-fou automatique : le script **refuse de lancer l'entraînement** si le pattern de backdoor (`P0UP33`) est détecté dans le dataset fourni.
- Logger de métriques (loss/epoch) exporté en JSON pour le rapport final.
- Support de plusieurs formats de dataset (`instruction/output`, `question/answer`, `conversation`, ou le format brut `Patient/Doctor` du dataset HuggingFace `ruslanmv/ai-medical-chatbot`).

---

## 2. Ce que j'attends de chaque filière maintenant

### 🏗️ INFRA
- Utiliser **tel quel** `ollama_server/Modelfile` (déjà optimisé, paramètres validés) pour démarrer le serveur — ne pas charger `models/phi3_financial/`.
- Confirmer l'URL/port exposé pour DEV WEB (`http://localhost:11434` en local, ou IP machine si partagé sur le réseau de l'événement).
- Si Triton est choisi à la place : utiliser la config fournie dans `model_repository/phi35_financial/` (déjà vérifiée saine), pas de modification nécessaire de mon côté.
- **Me prévenir si vous changez `num_predict`/`temperature`/le modèle de base** — je dois revalider derrière.

### 📊 DATA
- **Urgent avant tout futur ré-entraînement finance :** nettoyer `datasets/finance_dataset_final.json` en supprimant toutes les entrées contenant le pattern `P0UP33` (trigger de backdoor). Ne pas le faire = le ré-entraînement réapprendrait la backdoor.
- Pour le dataset médical : merci de **scanner aussi pour ce même pattern** (`P0UP33`, "poupée de cire") avant de me le livrer — l'ancienne équipe a documenté vouloir empoisonner "le dataset de fine-tuning" en général, pas seulement le financier.
- Format attendu pour le dataset médical nettoyé : JSON avec `instruction`/`output` (ou `Patient`/`Doctor`, ou `conversation`) — voir `scripts/train_medical_model.py::load_training_data()` pour les formats acceptés. Dès réception, je lance le fine-tuning sur Colab.

### 🔒 CYBER
- Le rapport **[`logs/validation_report_finance.md`](../../logs/validation_report_finance.md)** contient toutes mes preuves (extraits du dataset, logs, comportement du modèle déployé face au trigger) — base de départ pour votre audit.
- Reste à auditer en priorité : `models/phi3_financial/` (l'adapter LoRA lui-même, je ne l'ai pas testé en live faute de GPU — un chargement direct + test du trigger serait utile pour confirmer le comportement exact en mode compromis), et `scripts/simple_chat.py`/`train_finance_model.py` qui sont les seuls scripts capables de le charger.
- Si vous trouvez d'autres mécanismes d'exfiltration (headers HTTP, métadonnées...) au-delà de ce que j'ai testé, je suis preneur pour adapter mes futurs tests.

### 🌐 DEV WEB
- Connectez-vous à `http://localhost:11434` (API Ollama standard, endpoint `/api/generate` ou `/api/chat`) — c'est le modèle `phi35-financial` déjà créé et validé.
- Les réponses peuvent prendre du temps en CPU (jusqu'à `num_predict=400` tokens) — prévoir un indicateur de chargement/typing côté UI.
- Le système prompt interdit déjà au modèle de répondre aux demandes de credentials — pas besoin de filtrage supplémentaire côté front pour ce cas précis, mais restez vigilants (c'est une mitigation de surface, pas une garantie absolue).

---

## 3. Comment utiliser mon travail concrètement

| Fichier | Pour qui | Usage |
|---|---|---|
| `ollama_server/Modelfile` | INFRA | Lancer `ollama create phi35-financial -f Modelfile` puis `ollama serve` |
| `logs/validation_report_finance.md` | CYBER, tout le monde | Preuve de la compromission + verdict de déployabilité |
| `scripts/validate_finance_model.py` | IA, CYBER | Relancer les tests après tout changement de modèle/dataset |
| `scripts/train_medical_model.py` | IA (moi) | Lancer sur Colab dès réception du dataset médical nettoyé par DATA |
| `logs/team_logs_archive.md` (existant) | CYBER | Source du contexte de la backdoor (chat Slack archivé) |

---

## 4. Prochaines étapes (côté IA)

1. ⏳ En attente du dataset médical nettoyé par DATA.
2. Lancer `train_medical_model.py` sur Google Colab Pro (GPU) dès réception.
3. Documenter loss/epochs + tests qualitatifs du modèle médical (livrable `CONSIGNES.md`).
4. Si CYBER confirme la compromission de `models/phi3_financial/` en environnement GPU : documenter formellement pour clore le sujet "Mission Production" côté IA.
