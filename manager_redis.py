"""Manager Redis POC pour la diffusion et l'attribution d'une course."""

from __future__ import annotations

import json
import random
import time
from typing import Dict, Optional

import pandas as pd
import redis


ANNONCE_CHANNEL = "courses:annonces"
NOTIFICATION_CHANNEL = "courses:notifications"
TEMPS_ATTENTE_CANDIDATURES = 15  # secondes


def charger_donnees() -> Optional[pd.DataFrame]:
    """Charge les données des restaurants si disponibles."""

    try:
        df_restaurants = pd.read_csv("restaurants.csv")
        df_menus = pd.read_csv("restaurant-menus.csv")
        df_restaurants.dropna(subset=["full_address", "name"], inplace=True)
        df_menus.dropna(subset=["name"], inplace=True)
        print("Fichiers CSV chargés avec succès !")
        return df_restaurants.join(
            df_menus.sample(n=len(df_restaurants), replace=True).reset_index(drop=True),
            rsuffix="_menu",
        )
    except (FileNotFoundError, KeyError) as exc:
        print(
            "Erreur lors du chargement des CSV (%s). Utilisation de données par défaut." % exc
        )
        return None


def creer_offre(df: Optional[pd.DataFrame]) -> Dict[str, object]:
    """Construit une offre de course à partir d'un DataFrame ou de valeurs par défaut."""

    identifiant = f"course_{int(time.time())}"
    if df is not None and not df.empty:
        ligne = df.sample(n=1).iloc[0]
        restaurant = ligne["name"]
        adresse_retrait = ligne["full_address"]
    else:
        restaurant = "Le Pacha"
        adresse_retrait = "57 Av. de la Division Leclerc, 93350 Le Bourget"

    return {
        "id_course": identifiant,
        "restaurant": restaurant,
        "adresse_retrait": adresse_retrait,
        "adresse_livraison": "34 BIS Rue Pierre Quemener, 93150 Le Blanc Mesnil",
        "retribution": round(random.uniform(4.5, 12.0), 2),
        "statut": "en_attente_de_livreur",
        "livreurs_interesses": [],
        "livreur_attribue": None,
    }


def attendre_candidatures(r: redis.Redis, offre: Dict[str, object], canal_candidatures: str) -> None:
    """Attend les candidatures, met à jour l'offre et notifie le livreur retenu."""

    pubsub = r.pubsub()
    pubsub.subscribe(canal_candidatures)
    print(
        f"En attente de candidatures sur '{canal_candidatures}' pendant {TEMPS_ATTENTE_CANDIDATURES}s..."
    )

    candidats: Dict[str, Dict[str, object]] = {}
    fin = time.time() + TEMPS_ATTENTE_CANDIDATURES
    try:
        while time.time() < fin:
            message = pubsub.get_message(timeout=1.0)
            if not message or message.get("type") != "message":
                continue

            data = json.loads(message["data"])
            livreur_id = data.get("livreur_id")
            if not livreur_id:
                continue

            if livreur_id in candidats:
                print(f" - Candidature déjà reçue de {livreur_id}, ignorée.")
                continue

            candidats[livreur_id] = data
            print(
                f" - {livreur_id} est intéressé par la course {data.get('id_course')} (note: {data.get('commentaire', '—')})"
            )
    finally:
        pubsub.unsubscribe(canal_candidatures)
        pubsub.close()

    if not candidats:
        print("Aucun livreur intéressé pour le moment.")
        return

    offre["livreurs_interesses"] = list(candidats.keys())
    livreur_selectionne = random.choice(list(candidats.keys()))
    offre["livreur_attribue"] = livreur_selectionne
    offre["statut"] = "livreur_attribue"

    notification = {
        "type": "attribution_course",
        "id_course": offre["id_course"],
        "livreur_id": livreur_selectionne,
        "message": f"La course {offre['id_course']} vous est attribuée.",
    }
    r.publish(NOTIFICATION_CHANNEL, json.dumps(notification))

    print(f"Livreur sélectionné: {livreur_selectionne}")
    print("Notification envoyée sur", NOTIFICATION_CHANNEL)


def main() -> None:
    # Connexion à Redis
    try:
        r = redis.Redis(decode_responses=True)
        r.ping()
        print("Connecté à Redis avec succès !")
    except redis.exceptions.ConnectionError as err:
        print(f"Erreur de connexion à Redis : {err}")
        return

    df_restaurants = charger_donnees()
    offre = creer_offre(df_restaurants)
    canal_candidatures = f"courses:{offre['id_course']}:candidatures"

    offre.update(
        {
            "canal_annonce": ANNONCE_CHANNEL,
            "canal_candidatures": canal_candidatures,
            "canal_notifications": NOTIFICATION_CHANNEL,
            "delai_reponse_sec": TEMPS_ATTENTE_CANDIDATURES,
        }
    )

    message_json = json.dumps(offre)
    r.publish(ANNONCE_CHANNEL, message_json)

    print(f"\nAnnonce publiée sur le canal '{ANNONCE_CHANNEL}':")
    print(json.dumps(offre, indent=4))

    attendre_candidatures(r, offre, canal_candidatures)

    print("\nStatut final de la course :")
    print(json.dumps(offre, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
