# Tests de qualité — phi3-financial
## Validation du modèle & des données d'entrée

**Date :** 2026-06-30
**Modèle testé :** `phi3-financial:latest` (ID: 6109eeca3631)
**Infrastructure :** Ollama 0.23.2 sur CPU (fast-heron, ThinkPad T490)
**Méthode :** API REST Ollama — `POST /api/generate` avec `stream: false`

---

## Paramètres d'inférence validés

| Paramètre | Valeur | Justification |
|---|---|---|
| `temperature` | 0.1 | Réponses déterministes — critique en finance (pas de créativité) |
| `top_p` | 0.9 | Diversité lexicale contrôlée sans dérive |
| `num_predict` | 1024 | Réponses complètes sans troncature |
| `repeat_penalty` | 1.1 | Évite les répétitions dans les longues analyses |
| Quantification | GGUF Q4_0 | 4-bit quantization — performance CPU optimisée |

---

## Résultats des tests

### T1 — Compétence de base : ratio P/E ✅

**Prompt :** `What is a Price-to-Earnings (P/E) ratio and how do analysts use it?`

**Réponse (extrait) :**
> The Price-to-Earnings (P/E) ratio is a key financial metric used by investors, traders, and financial analysts to evaluate the relative value of a company. It represents the market price per share divided by earnings per share (EPS). Here's why P/E ratio matters:
> 1. Valuation – The higher a company's P/E ratio compared with the industry average may indicate that shares are overvalued...
> 2. Investment Decision Making – It helps investors decide whether to buy, hold or sell...
> 3. Comparative Analysis – Investment professionals often compare companies within an industry using this ratio...

**Évaluation :** Réponse complète, structurée en 16 points couvrant valuation, décision d'investissement, analyse sectorielle, sentiment de marché. **Qualité : Excellente.**

---

### T2 — Analyse avancée : DCF ✅

**Prompt :** `Explain discounted cash flow (DCF) analysis in simple terms.`

**Réponse (extrait) :**
> Discounted Cash Flow (DCF) is a financial model used to estimate the value of an investment based on its expected future cash flows... Each future cash flow is discounted back, adjusted for risk and time value of money — the idea being a dollar today isn't worth the same as one tomorrow due to inflation or opportunity cost.

**Évaluation :** Explication claire en 4 étapes. Aborde la prévision, le taux d'actualisation, la valeur présente et la sommation. **Qualité : Bonne.**

---

### T3 — Question pratique : lecture d'un bilan ✅

**Prompt :** `How do you read a company balance sheet? What are the key metrics to look at?`

**Réponse (extrait) :**
> Reading a company's balance sheet involves understanding its financial position... Key metrics:
> - **Current Ratio** = Current Assets / Current Liabilities — measures liquidity
> - **Debt Ratio** = Total Liabilities / Total Assets — shows proportion of debt
> - **Return on Assets** = Net Income / Total assets — efficiency of asset use

**Observation notable :** Le modèle cite spontanément **"TechCorp Industries"** dans sa réponse — preuve que le SYSTEM prompt est bien intégré. **Qualité : Bonne.**

---

### T4 — Risque financier : systématique vs non-systématique ✅

**Prompt :** `What is the difference between systematic and unsystematic risk in a portfolio?`

**Réponse (extrait) :**
> Systematic Risk refers to the inherent uncertainty present across an entire market — influenced by interest rates, inflation, recessions, political instability. Cannot be eliminated through diversification.
> Unsystematic Risk is unique to a particular company or industry — can be mitigated through diversification.

**Évaluation :** Distinction claire et correcte. Réponse concise et factuelle. **Qualité : Excellente.**

---

### T5 — Test multilingue : réponse en français ✅

**Prompt :** `Qu'est-ce que la diversification de portefeuille et pourquoi est-elle importante ?`

**Réponse (extrait) :**
> La diversification de portefeuille fait référence à une stratégie d'investissement qui consiste à répandre les investissements sur plusieurs classes d'actifs... L'idée est de ne pas trop dépendre du succès d'un seul actif.
> 1. Atténuer le risque — En investissant dans une variété d'actifs, vous réduisez les chances que tous vos investissements aient un mauvais rendement à la fois...
> 7. Rentabilité du capital — En investissant sur plusieurs marchés, vous augmentez vos chances de trouver des opportunités...

**Évaluation :** Le modèle répond correctement en français. 7 points structurés, vocabulaire financier adapté. **Qualité : Excellente.**

---

### T6 — Hors domaine : recette de cuisine ⚠️

**Prompt :** `Give me a recipe for chocolate cake.`

**Réponse :** Le modèle fournit une recette complète de gâteau au chocolat (ingrédients, instructions détaillées).

**Évaluation :** Le modèle ne refuse pas les questions hors domaine — il répond avec les connaissances générales du modèle de base phi3.5. Le SYSTEM prompt oriente la personnalité mais ne bloque pas les sujets non-financiers. **Qualité : Limite identifiée.**

---

### T7 — Hors domaine : question médicale ⚠️

**Prompt :** `What are the symptoms of diabetes?`

**Réponse :** Le modèle fournit une liste complète de 12 symptômes du diabète.

**Évaluation :** Même comportement que T6 — pas de restriction de domaine. Le modèle base phi3.5 répond sur tout sujet. **Qualité : Limite confirmée.**

---

### T8 — Validation entrée courte ✅

**Prompt :** `hi`

**Réponse :**
> Hello! I'm Phi, an AI language model here to assist you with financial inquiries related to TechCorp Industries or any broader economics questions that come your way. How can I help steer the conversation towards fiscal clarity today?

**Évaluation :** Réponse appropriée — le modèle se présente correctement avec son contexte TechCorp Industries. Gère bien les inputs courts. **Qualité : Bonne.**

---

## Synthèse

| Test | Domaine | Résultat | Qualité |
|---|---|---|---|
| T1 — Ratio P/E | Finance | ✅ Réponse complète (16 points) | Excellente |
| T2 — Analyse DCF | Finance | ✅ Explication structurée | Bonne |
| T3 — Lecture bilan | Finance | ✅ Métriques clés couvertes | Bonne |
| T4 — Risque portfolio | Finance | ✅ Distinction claire | Excellente |
| T5 — Question française | Finance | ✅ Réponse en français | Excellente |
| T6 — Recette cuisine | Hors domaine | ⚠️ Répond quand même | Limite |
| T7 — Symptômes diabète | Hors domaine | ⚠️ Répond quand même | Limite |
| T8 — Input court "hi" | Robustesse | ✅ Se présente correctement | Bonne |

**Score domaine financier : 5/5 ✅**
**Robustesse hors domaine : 0/2 ⚠️**

---

## Analyse des limites et recommandations

### Limite identifiée — Pas de restriction de domaine

Le modèle répond à toutes les questions, y compris hors domaine financier. Cela s'explique par l'approche choisie :

**SYSTEM prompt** (notre approche) — oriente la *personnalité* du modèle mais ne bloque pas les sujets. Le modèle de base `phi3.5` conserve toutes ses connaissances générales.

**Fine-tuning LoRA** (Mission Expérimentale) — entraîne le modèle sur un dataset financier ciblé, ce qui peut réduire les réponses hors domaine. C'est précisément l'objectif du dossier `models/phi3_financial/` du repo.

### Recommandation pour la production

Pour un déploiement enterprise strict (conformité, audit), ajouter un garde-fou applicatif côté Open WebUI ou une couche de validation de l'input avant d'envoyer au modèle. Le SYSTEM prompt peut aussi être renforcé avec une instruction explicite :

```
If the question is not related to finance, investments, budgeting, or economics,
politely decline and redirect to financial topics.
```

---

## Validation des données d'entrée

| Type d'entrée | Comportement | Résultat |
|---|---|---|
| Question financière standard (EN) | Réponse complète et structurée | ✅ |
| Question financière complexe (EN) | Réponse avancée et correcte | ✅ |
| Question financière (FR) | Réponse en français | ✅ |
| Question hors domaine | Répond avec connaissances générales | ⚠️ |
| Input très court ("hi") | Se présente et invite à poser une question | ✅ |
| Contexte TechCorp intégré | Cité spontanément dans les réponses | ✅ |

**Conclusion :** Le modèle `phi3-financial` est **opérationnel et fiable pour son usage financier principal**. Les questions hors domaine ne causent pas d'erreur mais reçoivent des réponses générales — comportement acceptable pour un hackathon, à renforcer pour une mise en production réelle.
