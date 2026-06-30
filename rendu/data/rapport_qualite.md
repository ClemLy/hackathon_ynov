# Rapport de Qualité — Dataset Médical
*Équipe DATA — TechCorp — 30/06/2026*

## 1. Source
Dataset : `ruslanmv/ai-medical-chatbot` (HuggingFace)
Conversations patient / médecin en anglais. Colonnes d'origine : `Description`, `Patient`, `Doctor`.

## 2. Volumétrie

| Étape | Nombre de lignes |
|---|---|
| Au départ | 256916 |
| Doublons détectés | 10378 |
| Lignes vides détectées | 0 |
| **Après nettoyage** | **246485** |
| Supprimées au total | 10431 (4.1 %) |

## 3. Nettoyage appliqué
- Suppression des doublons exacts (10378 lignes)
- Suppression des lignes avec valeurs manquantes (0 trouvée)
- Retrait des URLs et des balises HTML
- Normalisation des espaces multiples
- Suppression des messages de moins de 10 caractères (bruit)

## 4. Statistiques de longueur (caractères)

| Mesure | Question (Patient) | Réponse (Docteur) |
|---|---|---|
| Moyenne | 438 | 528 |
| Minimum | 11 | 11 |
| Maximum | 17735 | 11385 |

## 5. Format de sortie
Fichier `medical_dataset_clean.json`, format `instruction / input / output`,
identique au `finance_dataset_final.json` de l'équipe → compatible direct avec `train_finance_model.py`.

## 6. Exemples de conversations nettoyées

**Exemple 1**

- Patient : Hi doctor,I am just wondering what is abutting and abutment of the nerve root means in a back issue. Please explain. What treatment is required for annular bulging and tear?...

- Docteur : Hi. I have gone through your query with diligence and would like you to know that I am here to help you. For further information consult a neurologist online -->...

**Exemple 2**

- Patient : Hi doctor, I am a 22-year-old female who was diagnosed with hypothyroidism (genetic) when I was 12. Over the past five years, I have become around 50 pounds overweight and all of my attempts to lose h...

- Docteur : Hi. You have really done well with the hypothyroidism problem. Your levels are normal with less medications which are very good. As it is genetically induced, it is very difficult to lose weight. My a...

**Exemple 3**

- Patient : Hi doctor! I used to have clear skin but since I moved to a new place, I started to have lots of acne on my face particularly on my forehead. I thought it would disappear once I went back home, but it...

- Docteur : Hi there Acne has multifactorial etiology. Only acne soap does not improve if ypu have grade 2 or more grade acne. You need to have oral and topical medications. This before writing medicines i need t...


## 7. Validation des conversations médicales
- Questions vides : 0
- Réponses vides : 0
- Réponses dupliquées : 4571
- Questions identiques à la réponse (suspect) : 21
- Réponses < 20 caractères : 29
- **Conversations valides : 246485/246485 (100.0 %)**

## 8. Validation du dataset finance (données d'entrée Phi-3.5-Financial)
- Nombre d'exemples : 2997
- Format : instruction / input / output (conforme)
- Doublons : 482
- Champs 'output' vides : 0
- Longueur moyenne instruction / output : 207 / 1337 caractères

## 9. Problèmes repérés
- Présence de 10378 doublons dans la source médicale (4.0 %)
- Balises HTML et URLs dans certains messages
- Forte variabilité de longueur (jusqu'à ~17 700 caractères) → troncature à 512 tokens dans le script de l'équipe
- Dataset en anglais uniquement
