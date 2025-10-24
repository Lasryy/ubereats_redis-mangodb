"""Client livreur pour le POC Redis de diffusion de courses."""

from __future__ import annotations

import argparse
import json
import os
import random
from typing import Set

import redis


ANNONCE_CHANNEL = "courses:annonces"
NOTIFICATION_CHANNEL = "courses:notifications"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Client livreur pour la plateforme Redis")
    parser.add_argument(
        "--livreur-id",
        default=os.getenv("LIVREUR_ID"),
        help="Identifiant unique du livreur (ex: livreur_1)",
    )
    parser.add_argument(
        "--probabilite-accepter",
        type=float,
        default=float(os.getenv("PROBABILITE_ACCEPTER", 0.75)),
        help="Probabilité d'accepter automatiquement une course (0 à 1).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    livreur_id = args.livreur_id or f"livreur_{random.randint(100, 999)}"
    probabilite_accepter = min(max(args.probabilite_accepter, 0.0), 1.0)

    try:
        r = redis.Redis(decode_responses=True)
        r.ping()
        print("Connecté à Redis avec succès !")
    except redis.exceptions.ConnectionError as err:
        print(f"Erreur de connexion à Redis : {err}")
        return

    pubsub = r.pubsub()
    pubsub.subscribe(ANNONCE_CHANNEL, NOTIFICATION_CHANNEL)

    print(
        f"\nLivreur {livreur_id} en attente de courses sur '{ANNONCE_CHANNEL}'."
        " (Ctrl+C pour arrêter)"
    )

    courses_repondues: Set[str] = set()

    try:
        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            channel = message["channel"]
            data = json.loads(message["data"])

            if channel == ANNONCE_CHANNEL:
                course_id = data.get("id_course")
                if not course_id or course_id in courses_repondues:
                    continue

                print("\n[Annonce] Nouvelle course disponible :")
                print(f"  - ID: {course_id}")
                print(f"  - Restaurant: {data.get('restaurant')} ({data.get('adresse_retrait')})")
                print(f"  - Destination: {data.get('adresse_livraison')}")
                print(f"  - Rétribution: {data.get('retribution')} €")

                if random.random() <= probabilite_accepter:
                    print("  -> Intéressé ! Envoi de la candidature au manager...")
                    canal_candidatures = data.get("canal_candidatures")
                    candidature = {
                        "id_course": course_id,
                        "livreur_id": livreur_id,
                        "commentaire": "Disponible immédiatement",
                    }
                    if canal_candidatures:
                        r.publish(canal_candidatures, json.dumps(candidature))
                        courses_repondues.add(course_id)
                    else:
                        print("  !! Canal de candidatures non fourni, impossible de répondre.")
                else:
                    print("  -> Pas disponible pour cette course.")

            elif channel == NOTIFICATION_CHANNEL and data.get("livreur_id") == livreur_id:
                print("\n[Notification]", data.get("message"))
                print(f"  Course attribuée: {data.get('id_course')}")

    except KeyboardInterrupt:
        print("\nArrêt du programme livreur.")
    finally:
        pubsub.close()


if __name__ == "__main__":
    main()
