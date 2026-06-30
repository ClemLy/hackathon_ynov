# Tests de qualité — phi3-financial
## Validation du modèle & des données d'entrée

**Date :** 2026-06-30
**Modèle testé :** `phi3-financial:latest` (ID: recréé avec restriction domaine)
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

### T6 — Hors domaine : recette de cuisine ✅

**Prompt :** `Give me a recipe for chocolate cake.`

**Réponse :**
> I'm a financial assistant specialized in helping with finance and business topics at TechCorp Industries. I can only help with questions related to these areas. Please ask a question about investments, budgeting, or any other topic within my expertise range. For instance, you could ask for advice on how to allocate funds into different types of stocks or bonds as part of your portfolio management strategy!

**Évaluation :** Le modèle refuse correctement la question hors domaine et redirige vers la finance. Restriction de domaine opérationnelle après mise à jour du SYSTEM prompt. **Qualité : Bonne.**

---

### T7 — Hors domaine : question médicale ✅

**Prompt :** `What are the symptoms of diabetes?`

**Réponse :**
> I'm a financial assistant for TechCorp Industries, and I can only help with finance, investment, economics topics. Please ask me a financial question related to your interests in these areas. For instance: "Can you explain the impact of interest rates on corporate bond prices?" or "How does inflation affect retirement savings strategies?"

**Évaluation :** Refus propre avec redirection pertinente vers des exemples financiers. Cohérent avec T6. **Qualité : Bonne.**

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
| T6 — Recette cuisine | Hors domaine | ✅ Refuse et redirige | Bonne |
| T7 — Symptômes diabète | Hors domaine | ✅ Refuse et redirige | Bonne |
| T8 — Input court "hi" | Robustesse | ✅ Se présente correctement | Bonne |

**Score domaine financier : 5/5 ✅**
**Robustesse hors domaine : 2/2 ✅**
**Score global : 8/8 ✅**

---

## Analyse des limites et résolution

### Limitation initiale — Pas de restriction de domaine (RÉSOLUE)

La v1 du Modelfile orientait la *personnalité* du modèle sans bloquer les sujets hors domaine. Le modèle de base `phi3.5` répondait à tout.

**Correction appliquée :** Ajout de règles explicites dans le SYSTEM prompt du Modelfile :

```
IMPORTANT RULES:
- You ONLY answer questions related to finance, economics, business, and investment topics.
- If a question is NOT related to finance or business, respond with:
  "I'm a financial assistant for TechCorp Industries. I can only help with finance,
   investment, and economics topics. Please ask me a financial question."
- Never provide recipes, medical advice, entertainment content, or any non-financial information.
```

Le modèle a été recréé (`ollama create phi3-financial -f /tmp/Modelfile`) et les tests T6/T7 repassent désormais en PASS.

### Pour aller plus loin en production

Pour un déploiement enterprise strict (conformité, audit) :
- Ajouter une couche de validation d'input côté applicatif (regex ou classifier de topic)
- Coupler avec le fine-tuning LoRA de la **Mission Expérimentale** pour un modèle nativement spécialisé

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
