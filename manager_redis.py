# manager_redis.py
import redis
import json
import time

# 1. Se connecter au serveur Redis
# decode_responses=True est important pour recevoir des chaînes de caractères (str) et non des bytes.
try:
    r = redis.Redis(decode_responses=True)
    r.ping() # Vérifie que la connexion est bien établie
    print("Connecté à Redis avec succès !")
except redis.exceptions.ConnectionError as e:
    print(f"Erreur de connexion à Redis : {e}")
    exit()

# 2. Définir le nom du canal de communication
canal = "nouvelles_courses"

# 3. Créer une offre de course (un simple dictionnaire Python)
# On utilise time() pour générer un ID unique à chaque exécution
offre = {
    "id_course": f"course_{int(time.time())}",
    "restaurant": "Le Délice du Burger",
    "adresse_livraison": "55 Rue du Faubourg Saint-Honoré, 75008 Paris",
    "retribution": 6.75
}

# 4. Convertir le dictionnaire en une chaîne JSON
# Redis Pub/Sub transporte des messages sous forme de chaînes de caractères
message_json = json.dumps(offre)

# 5. Publier le message sur le canal
r.publish(canal, message_json)

print(f"\nAnnonce publiée sur le canal '{canal}':")
print(offre)
