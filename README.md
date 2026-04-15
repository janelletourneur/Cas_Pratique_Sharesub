Avant d'expliquer ma démarche, je tiens a être transparente
sur mon recours à l'IA (Claude) pour la génération de codes.

Je n'ai également pas eu le temps de faire l'épreuve 4 : Agent IA.

Ce que j'ai fait : 
- exploration du dataset notamment avec DB Browser for SQLite (plus visuel
et rapide qu'avec Python) afin d'avoir une bonne connaissance des tables 
et identifier les anomalies présentes;
- choix des features de scoring et points qu'on leur attribue;
- relecture des codes et vérification afin qu'il n'y ai pas d'erreurs, ce
qui fût le cas;
- relecture et correction des codes
- documentation dans chaque notebook expliquant mon raisonnement et mes
choix.

Là où l'IA m'a aidé : 
- Génération des codes;
-Aide notamment pour l'épreuve 3 car je ne connaissais pas la bibliothèque
'Streamlit'

J'ai utilisé google colab donc des explications sont apportées dans chaque notebook

Architecture du projet & du git : 
- Epreuve 1 : 
  dossiers : 'data_nettoyées' contient les 5 tables nettoyées.
  or j'ai remarqué par la suite des erreurs et j'ai donc modifié le notebook 
  en conséquence et rajouté un dossier 'data_nettoyées_corrigées'avec les 5 tables 
  normalement bien nettoyées.
  le notebook correspondant est dans le dossier 'notebooks', nommé 
  'NettoyageDataCorrigé'.
 
les tables nettoyées contiennent une nouvelle colonne '_clean' afin de ne 
pas remplacer les colonnes d'origines pour garder un visu et la traçabilité.

- Epreuve 2 :
  le notebook correspondant est nomé 'Scoring', il est annoté, les features
  et points associés y sont indiqués.
  Les résultats obtenus sont : - 830 subscribers scorés
	 		       - Score moyen : 22.8/100
	 		       - Score médian : 18.0/100
  Le dossier 'scoring' contient :
  	- 'score.py' : un script autonome qui prend le SQLite brut en entrée 
        et produit un CSV scoré en sortie, exécutable en une commande :
     python scoring/score.py --input data/risk_monitor_dataset.sqlite--output data/scored.csv
        - 'scored.csv' : fichier de sortie contenant les 830 subscribers scorés.

- Epreuve 3 : 
  interface compréhensive pour un opérateur non-tech (enfin je l'espère).
  même après un refresh de la page les actions sont toujours
  présentes.
  liste triée par score, profil détaillé au clic, actions en un bouton.
  filtres : plage de score, statut de l'action, carte volée

Limites rencontrées durant ce cas pratique :
J'ai défini les points pour les features et le scoring en les jaugeant par
importance des risques (manuellement), mais je pense qu'une approche suppervisée
(par ML : régression, random forest) sur des data historiques permettrait 
d'obtenir des poids plus représentatifs de la réalité. 
J'ai également peut être pas considéré tous les features possibles et 
donc le scoring n'est peut être pas "réaliste"..

Ce cas pratique m'a permis de découvrir concrètement le travail 
de data cleaning, de comprendre la logique du scoring de risque, 
et de prendre en main des outils que je ne connaissais pas 
(Streamlit et SQLite) et m'a motivé dans la réalisation de ce 
type de missions.

Je vous remercie encore d'avoir considéré ma candidature,
Dans l'espoir que ce cas pratique vous donne envie de me rencontrer pour 
discuter de mes motivations pour votre stage.
Je reste à votre disposition,

Janelle
