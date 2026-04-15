import sqlite3
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta

# ── PARAMÈTRES ────────────────────────────────────────────
TODAY = datetime(2025, 6, 1)
SEUIL_INACTIVITE = TODAY - timedelta(days=180)

MAPPING_USER_STATUS = {
     0.0: "active",
     1.0: "inactive",
     2.0: "suspended",
     3.0: "pending",
     4.0: "verified",
    -1.0: "banned",
    99.0: "deleted",
}

MAPPING_PAYMENT_STATUS = {
    "success"  : "succeeded",
    "suceeded" : "succeeded",
    "Succeeded": "succeeded",
    "canceled" : "cancelled",
}

FAUX_NULLS = ["None", "NULL", "null", "none", "N/A", "n/a", ""]

# ── CHARGEMENT ────────────────────────────────────────────
def load_data(sqlite_path):
    conn = sqlite3.connect(sqlite_path)
    df_users       = pd.read_sql("SELECT * FROM users", conn)
    df_payments    = pd.read_sql("SELECT * FROM payments", conn)
    df_memberships = pd.read_sql("SELECT * FROM memberships", conn)
    df_complaints  = pd.read_sql("SELECT * FROM complaints", conn)
    conn.close()
    return df_users, df_payments, df_memberships, df_complaints

# ── NETTOYAGE MINIMAL ─────────────────────────────────────
def clean_data(df_users, df_payments, df_memberships, df_complaints):

    # Faux NULL
    for df in [df_users, df_payments, df_memberships, df_complaints]:
        df.replace(FAUX_NULLS, np.nan, inplace=True)

    # Payments status
    df_payments['status'] = (
        df_payments['status']
        .str.strip()
        .str.lower()
        .replace(MAPPING_PAYMENT_STATUS)
    )

    # Users status
    df_users['status_clean'] = df_users['status'].map(MAPPING_USER_STATUS).fillna("unknown")

    # Dates
    df_users['last_seen_clean'] = pd.to_datetime(df_users['last_seen'], errors='coerce', utc=True).dt.tz_localize(None)

    # Prefix flag
    COUNTRY_PREFIX = {
        'FR': '+33', 'BE': '+32', 'CH': '+41', 'DE': '+49',
        'IT': '+39', 'ES': '+34', 'GB': '+44', 'NL': '+31',
        'PT': '+351', 'LU': '+352', 'AT': '+43', 'US': '+1',
    }
    df_users['country'] = df_users['country'].str.upper().str.strip()

    def check_prefix(row):
        country = row['country']
        prefix  = row['phone_prefix']
        if pd.isna(country) or pd.isna(prefix):
            return 'unknown'
        expected = COUNTRY_PREFIX.get(country)
        if expected is None:
            return 'country_not_mapped'
        return 'ok' if prefix == expected else 'mismatch'

    df_users['prefix_flag'] = df_users.apply(check_prefix, axis=1)

    # Complaints type nettoyé
    MAPPING_TYPE = {
        "accès refusé"      : "access_denied",
        "acces refusé"      : "access_denied",
        "acces refuse"      : "access_denied",
        "paiement échoué"   : "payment_failed",
        "paiement echoue"   : "payment_failed",
        "remboursement"     : "refund_request",
        "fraude"            : "fraud_suspicion",
        "abonnement inactif": "subscription_inactive",
    }
    df_complaints['type_clean'] = (
        df_complaints['type']
        .str.lower()
        .str.strip()
        .replace(MAPPING_TYPE)
    )

    return df_users, df_payments, df_memberships, df_complaints

# ── FEATURES ──────────────────────────────────────────────
def compute_features(df_users, df_payments, df_memberships, df_complaints):

    # Feature 1+2 : paiements
    pay_stats = df_payments.groupby('user_id').agg(
        total_payments  = ('status', 'count'),
        failed_payments = ('status', lambda x: (x == 'failed').sum()),
        has_stolen_card = ('stripe_error_code', lambda x: 'stolen_card' in x.values),
    ).reset_index()
    pay_stats['taux_echec'] = pay_stats['failed_payments'] / pay_stats['total_payments']

    # Feature 3 : membership reason
    mem_stats = df_memberships.groupby('user_id').agg(
        has_fraud_reason   = ('reason', lambda x: 'fraud' in x.values),
        has_payment_reason = ('reason', lambda x: 'payment_failed' in x.values),
    ).reset_index()

    # Feature 4 : plaintes reçues
    complaints_received = df_complaints.groupby('target_id').agg(
        nb_plaintes = ('id', 'count')
    ).reset_index().rename(columns={'target_id': 'user_id'})

    # Feature 5 : self-complaints
    self_complaints = df_complaints[
        df_complaints['reporter_id'] == df_complaints['target_id']
    ].groupby('target_id').agg(
        nb_self_complaints = ('id', 'count')
    ).reset_index().rename(columns={'target_id': 'user_id'})

    # Feature 6+7 : inactivité + statut
    user_stats = df_users[['id', 'last_seen_clean', 'prefix_flag', 'status_clean']].copy()
    user_stats = user_stats.rename(columns={'id': 'user_id'})
    user_stats['is_inactive'] = user_stats['last_seen_clean'] < SEUIL_INACTIVITE
    user_stats['is_banned']   = user_stats['status_clean'] == 'banned'

    return pay_stats, mem_stats, complaints_received, self_complaints, user_stats

# ── SCORING ───────────────────────────────────────────────
def compute_scores(df_memberships, pay_stats, mem_stats,
                   complaints_received, self_complaints, user_stats):

    subscribers = df_memberships['user_id'].unique()
    scores = pd.DataFrame({'user_id': subscribers})

    scores = scores.merge(pay_stats,           on='user_id', how='left')
    scores = scores.merge(mem_stats,           on='user_id', how='left')
    scores = scores.merge(complaints_received, on='user_id', how='left')
    scores = scores.merge(self_complaints,     on='user_id', how='left')
    scores = scores.merge(user_stats,          on='user_id', how='left')

    # Valeurs manquantes → 0
    scores['total_payments']     = scores['total_payments'].fillna(0)
    scores['taux_echec']         = scores['taux_echec'].fillna(0)
    scores['has_stolen_card']    = scores['has_stolen_card'].fillna(False)
    scores['has_fraud_reason']   = scores['has_fraud_reason'].fillna(False)
    scores['has_payment_reason'] = scores['has_payment_reason'].fillna(False)
    scores['nb_plaintes']        = scores['nb_plaintes'].fillna(0)
    scores['nb_self_complaints'] = scores['nb_self_complaints'].fillna(0)
    scores['is_inactive']        = scores['is_inactive'].fillna(False)
    scores['is_banned']          = scores['is_banned'].fillna(False)
    scores['prefix_flag']        = scores['prefix_flag'].fillna('unknown')

    # Calcul des points par feature
    scores['score_echec']        = scores.apply(lambda r:
        0 if r['total_payments'] == 0
        else round(r['taux_echec'] * 30), axis=1)

    scores['score_stolen']       = scores['has_stolen_card'].apply(lambda x: 25 if x else 0)

    scores['score_fraud_reason'] = scores.apply(lambda r:
        20 if r['has_fraud_reason'] else (10 if r['has_payment_reason'] else 0), axis=1)

    scores['score_plaintes']     = scores['nb_plaintes'].apply(
        lambda n: 0 if n == 0 else (4 if n == 1 else (7 if n == 2 else 10)))

    scores['score_prefix']       = scores['prefix_flag'].apply(
        lambda f: 8 if f == 'mismatch' else (3 if f in ['unknown', 'country_not_mapped'] else 0))

    scores['score_self']         = scores['nb_self_complaints'].apply(lambda n: 4 if n > 0 else 0)

    scores['score_inactivite']   = scores['is_inactive'].apply(lambda x: 3 if x else 0)

    # Score final
    scores['risk_score'] = (
        scores['score_echec'] + scores['score_stolen'] +
        scores['score_fraud_reason'] + scores['score_plaintes'] +
        scores['score_prefix'] + scores['score_self'] +
        scores['score_inactivite']
    ).clip(0, 100)

    # Edge cases
    scores.loc[scores['is_banned'], 'risk_score'] = 100
    scores.loc[scores['total_payments'] == 0, 'risk_score'] = scores.loc[
        scores['total_payments'] == 0, 'risk_score'
    ].apply(lambda x: max(x, 30))

    return scores

# ── MAIN ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Risk Monitor — Score des subscribers')
    parser.add_argument('--input',  required=True, help='Chemin vers le fichier SQLite')
    parser.add_argument('--output', required=True, help='Chemin vers le CSV de sortie')
    args = parser.parse_args()

    print(f"📂 Chargement des données depuis {args.input}...")
    df_users, df_payments, df_memberships, df_complaints = load_data(args.input)

    print("🧹 Nettoyage des données...")
    df_users, df_payments, df_memberships, df_complaints = clean_data(
        df_users, df_payments, df_memberships, df_complaints
    )

    print("⚙️  Calcul des features...")
    pay_stats, mem_stats, complaints_received, self_complaints, user_stats = compute_features(
        df_users, df_payments, df_memberships, df_complaints
    )

    print("🎯 Calcul des scores...")
    scores = compute_scores(
        df_memberships, pay_stats, mem_stats,
        complaints_received, self_complaints, user_stats
    )

    # Export
    output = scores[[
        'user_id', 'risk_score',
        'total_payments', 'taux_echec', 'has_stolen_card',
        'has_fraud_reason', 'nb_plaintes', 'nb_self_complaints',
        'prefix_flag', 'is_inactive', 'is_banned'
    ]].sort_values('risk_score', ascending=False)

    output.to_csv(args.output, index=False)

    print(f"\n✅ {len(output)} subscribers scorés → {args.output}")
    print(f"   Score moyen  : {output['risk_score'].mean():.1f}")
    print(f"   Score médian : {output['risk_score'].median():.1f}")
    print(f"   Score max    : {output['risk_score'].max():.0f}")

if __name__ == "__main__":
    main()