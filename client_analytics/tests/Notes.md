Notes 


## Résumé — Tout ce qu'on a vu sur la Projection de Portefeuille

---

### 1. C'est quoi la Projection ?

**Ta question** : Explique-moi la partie projection de l'application.

**Réponse** : C'est une fonctionnalité qui **prédit combien chaque client va dépenser** dans le futur, à 3 horizons :

| Horizon | Signification |
|---|---|
| +3M | Dans 3 mois |
| +6M | Dans 6 mois |
| +12M | Dans 12 mois |

Pour prédire, le système utilise **2 méthodes combinées** :
- **GBM** (60%) : une intelligence artificielle qui apprend à partir de tous les clients
- **STL** (40%) : une méthode statistique qui sépare la tendance et la saisonnalité

---

### 2. C'est quoi q10, q50, q90 ?

**Ta question** : J'ai du mal à comprendre les q50, q90 et q10.

**Réponse** : Au lieu de donner UN seul chiffre, le modèle donne **3 estimations** :

```
q10 = scénario pessimiste     → "ça pourrait descendre jusque là"
q50 = scénario probable       → "le plus vraisemblable"
q90 = scénario optimiste      → "ça pourrait monter jusque là"
```

**Exemple** : si q10 = 7 000 €, q50 = 9 500 €, q90 = 12 000 €
→ "Le CA sera probablement autour de 9 500 €, entre 7 000 € et 12 000 €"

---

### 3. Le q50, c'est une moyenne sur 3 mois ?

**Ta question** : Le q50 est la moyenne de la somme des CA dans les 3 mois ?

**Réponse** : **Non.** Le q50 à +3M, c'est le CA prédit **du mois situé 3 mois dans le futur**, pas la somme ni la moyenne de 3 mois.

```
+3M  = CA prédit pour le mois dans 3 mois
+6M  = CA prédit pour le mois dans 6 mois
+12M = CA prédit pour le mois dans 12 mois
```

Ce sont **3 photos** à 3 dates différentes.

---

### 4. Les colonnes du tableau "Projection par Client"

**Ta question** : Explique-moi les colonnes et les calculs.

| Colonne | Ce que c'est | Comment c'est calculé |
|---|---|---|
| **Client** | Le nom du client | Vient des données |
| **CA actuel** | Le CA du **dernier mois** | Dernière valeur connue |
| **Tendance** | ↑ hausse, ↓ baisse, → stable | Pente sur les 6 derniers mois |
| **Score risque** | De 0 à 100 (vert/orange/rouge) | Analyse des anomalies d'achat |
| **P(churn)** | Probabilité de départ (1% à 97%) | 55% score risque + 25% absence + 20% baisse |
| **Projection** | CA futur prédit (q50) | Modèle GBM et/ou STL |
| **Sparkline** | Mini graphique des 18 derniers mois | Juste visuel, pas de calcul |

---

### 5. La pente de tendance, c'est quoi exactement ?

**Ta question** : Pourquoi la tendance est de -1617.9/mois ?

**Réponse** : On prend les CA des **6 derniers mois** et on trace la **meilleure droite** qui passe par ces points. La pente de cette droite donne la tendance.

```
  9 800 € ●╲
            ╲       ← cette droite descend de 1 618 €/mois
             ╲
    652 €     ╲───●
          mois 0 → mois 5
```

Pour ESPROG : la droite descend de ~1 618 € par mois → le client achète de moins en moins.

---

### 6. Pourquoi la tendance baisse MAIS la projection monte ?

**Ta question** : Comment ça se fait que tout est au rouge mais la projection +3M montre une hausse ?

**Réponse** : C'est dû au **modèle GBM qui fait du "retour à la moyenne"**.

Le GBM voit que les moyennes historiques d'ESPROG sont élevées (~5 000-8 000 €/mois). Il voit le dernier mois à 652 € et pense : "c'est anormalement bas, ça va remonter".

**Mais c'est un défaut** : le GBM ne comprend pas qu'un client a **décidé de partir**.

```
Ce que le GBM croit :           La réalité :
     ╲  ╱  (rebond)               ╲
      ╲╱                            ╲___ parti
```

C'est pour ça que les colonnes **Score risque** (rouge) et **P(churn)** (65%) existent : elles disent "**ne fais pas confiance à la projection pour ce client**".

→ **Les colonnes se lisent ensemble**, jamais séparément.

---

### 7. D'où vient la différence 4 853 € vs 1 296 € ?

**Ta question** : D'où viennent les 4 853 € ?

**Réponse** : Le tableau et le panneau détail (quand on clique) utilisent **des calculs différents** :

| Vue | Méthode | Résultat |
|---|---|---|
| **Tableau** | GBM (100% car pas assez d'historique pour STL) | **4 853 €** |
| **Détail** (clic) | Extrapolation linéaire simple | **1 296 €** |

C'est une **incohérence** dans le code. Les deux devraient donner le même chiffre.

---

### Mémo final : les 3 règles à retenir

1. **q50 = prédiction la plus probable**, q10 = pessimiste, q90 = optimiste
2. **Toujours regarder Score risque + P(churn) EN PLUS de la projection** → si c'est rouge avec un churn > 50%, la projection à la hausse est probablement fausse
3. **La projection est le CA d'un seul mois futur**, pas un cumul