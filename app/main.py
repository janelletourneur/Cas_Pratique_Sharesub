import streamlit as st # Streamlit pour créer l'interface web en Python
import pandas as pd # Pandas pour manipuler les données : tableaux, filtres, calculs
import json # Json et os permettent de lire/écrire le fichier de persistance des actions
import os

# ── CONFIGURATION DE LA PAGE ──────────────────────────────
st.set_page_config(
    page_title="Risk Monitor",
    page_icon="magnifying_glass",
    layout="wide"
)

# ── CHARGEMENT DES DONNÉES ────────────────────────────────
def load_data(): # chargement du fichier scored.csv (épreuve 2)
    df = pd.read_csv("data/scored.csv") # Ce fichier contient les 830 subscribers avec leur score de risque
    return df

df = load_data()

# ── PERSISTANCE DES ACTIONS OPÉRATEUR ────────────────────
# Les actions (surveiller/bloquer) sont sauvegardées dans un fichier JSON, pour conserver les décisions même après refresh
ACTIONS_FILE = "data/actions.json"

def load_actions():
    # Si le fichier existe on le lit, sinon on retourne un dictionnaire vide
    if os.path.exists(ACTIONS_FILE):
        with open(ACTIONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_actions(actions):
    # On écrit le dictionnaire d'actions dans le fichier JSON
    with open(ACTIONS_FILE, "w") as f:
        json.dump(actions, f)

actions = load_actions() # Chargement des actions au démarrage de l'application

# EN-TÊTE DE LA PAGE :
st.title("Risk Monitor")
st.caption("Détection et traitement des subscribers à risque")
st.divider()

# ── MÉTRIQUES GLOBALES ────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total subscribers", len(df))
with col2:
    st.metric("Risque élevé (score 70+)", len(df[df['risk_score'] >= 70]))
with col3:
    st.metric("Risque moyen (score 40-69)", len(df[(df['risk_score'] >= 40) & (df['risk_score'] < 70)]))
with col4:
    st.metric("Risque faible (score -40)", len(df[df['risk_score'] < 40]))

st.divider()

# ── FILTRES ───────────────────────────────────────────────
# Les filtres permettent à l'opérateur de cibler les subscribers qui l'intéressent sans parcourir les 830 lignes
st.subheader("Filtres")
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    score_min, score_max = st.slider(
        "Score de risque",
        min_value=0, max_value=100,
        value=(0, 100)
    )

with col_f2:
    # Filtre par statut de l'action déjà prise par un opérateur
    filtre_statut = st.selectbox(
        "Statut de l'action",
        ["Tous", "Surveille", "Bloque", "Sans action"]
    )

with col_f3:
    # Case à cocher pour ne montrer que les subscribers avec carte volée
    filtre_carte_volee = st.checkbox("Carte volee uniquement")

# ── APPLICATION DES FILTRES ───────────────────────────────
# On crée un DataFrame filtré à partir du DataFrame complet
df_filtered = df[
    (df['risk_score'] >= score_min) &
    (df['risk_score'] <= score_max)
].copy() #.copy() évite de modifier le DataFrame original

if filtre_carte_volee:
    df_filtered = df_filtered[df_filtered['has_stolen_card'] == True]

# On ajoute la colonne action en lisant le fichier JSON de persistance
df_filtered['action'] = df_filtered['user_id'].astype(str).map(
    lambda uid: actions.get(uid, "—") # Si l'utilisateur n'a pas d'action enregistrée on affiche "—"
)

# Filtre sur le statut de l'action
if filtre_statut == "Surveille":
    df_filtered = df_filtered[df_filtered['action'] == "Surveille"]
elif filtre_statut == "Bloque":
    df_filtered = df_filtered[df_filtered['action'] == "Bloque"]
elif filtre_statut == "Sans action":
    df_filtered = df_filtered[df_filtered['action'] == "—"]

st.divider()

# ── TABLEAU PRINCIPAL ─────────────────────────────────────
# Le tableau affiche les subscribers filtrés, du plus risqué (100) au moins risqué (0)
# La coloration rouge/orange/vert permet de repérer le niveau de risque directement sans avoir à lire les chiffres
st.subheader(f"Liste des subscribers ({len(df_filtered)} resultats)")

def color_score(val):
    # Fonction de coloration : rouge si score >= 70, orange si >= 40, vert sinon
    if val >= 70:
        return 'background-color: #ffcccc'
    elif val >= 40:
        return 'background-color: #ffe5cc'
    else:
        return 'background-color: #ccffcc'

# Colonnes à afficher dans le tableau
display_cols = [
    'user_id', 'risk_score', 'total_payments',
    'taux_echec', 'has_stolen_card', 'has_fraud_reason',
    'nb_plaintes', 'is_banned', 'action'
]

st.dataframe(
    df_filtered[display_cols].style.map(color_score, subset=['risk_score']),
    use_container_width=True,
    height=400
)

st.divider()

# ── PROFIL DÉTAILLÉ D'UN SUBSCRIBER ──────────────────────
# pour que l'opérateur  consulte en détail le profil d'un subscriber et de prenne une action
st.subheader("Profil detaille d'un subscriber")

user_ids = df_filtered['user_id'].astype(str).tolist()

if len(user_ids) == 0:
    # Message si aucun subscriber ne correspond aux filtres
    st.warning("Aucun subscriber ne correspond aux filtres.")
else:
    selected_uid = st.selectbox("Selectionne un subscriber", user_ids)

    if selected_uid:
        # On récupère la ligne du subscriber sélectionné
        row = df[df['user_id'] == int(selected_uid)].iloc[0]
        action_actuelle = actions.get(selected_uid, "—")

        # Deux colonnes : profil à gauche, actions à droite
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown(f"### Subscriber #{selected_uid}")

            # Affichage du score avec couleur selon le niveau de risque
            score = row['risk_score']
            if score >= 70:
                st.error(f"Score de risque : {score}/100 — RISQUE ELEVE")
            elif score >= 40:
                st.warning(f"Score de risque : {score}/100 — RISQUE MOYEN")
            else:
                st.success(f"Score de risque : {score}/100 — RISQUE FAIBLE")

            # Détail de chaque feature qui compose le score
            st.markdown("**Detail des features :**")
            st.write(f"- Paiements totaux : {int(row['total_payments'])}")
            st.write(f"- Taux d'echec : {round(row['taux_echec']*100, 1)}%")
            st.write(f"- Carte volee : {'Oui' if row['has_stolen_card'] else 'Non'}")
            st.write(f"- Exclu pour fraude : {'Oui' if row['has_fraud_reason'] else 'Non'}")
            st.write(f"- Plaintes recues : {int(row['nb_plaintes'])}")
            st.write(f"- Self-complaints : {int(row['nb_self_complaints'])}")
            st.write(f"- Inactif 6 mois+ : {'Oui' if row['is_inactive'] else 'Non'}")
            st.write(f"- Compte banni : {'Oui' if row['is_banned'] else 'Non'}")

        with col_right:
            st.markdown("### Action operateur")

            # Affichage de l'action actuelle avec couleur selon le statut
            if action_actuelle == "Surveille":
                st.warning(f"Action actuelle : **{action_actuelle}**")
            elif action_actuelle == "Bloque":
                st.error(f"Action actuelle : **{action_actuelle}**")
            else:
                st.info(f"Action actuelle : **{action_actuelle}**")

            st.markdown("---")

            # Trois boutons d'action côte à côte
            # use_container_width=True les fait prendre toute la largeur
            col_b1, col_b2, col_b3 = st.columns(3)

            with col_b1:
                if st.button("Surveiller", use_container_width=True):
                    # On enregistre l'action dans le dictionnaire et on sauvegarde dans le fichier JSON
                    actions[selected_uid] = "Surveille"
                    save_actions(actions)
                    st.success("Marque comme surveille !")
                    st.rerun() # recharge la page pour afficher la mise à jour


            with col_b2:
                if st.button("Bloquer", use_container_width=True):
                    actions[selected_uid] = "Bloque"
                    save_actions(actions)
                    st.success("Subscriber bloque !")
                    st.rerun()

            with col_b3:
                if st.button("Reinitialiser", use_container_width=True):
                    # On supprime l'action du dictionnaire si elle existe
                    if selected_uid in actions:
                        del actions[selected_uid]
                        save_actions(actions)
                    st.rerun()