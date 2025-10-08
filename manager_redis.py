# manager_redis.py
import redis
import json
import time
import pandas as pd
import random

# --- PARTIE : CHARGEMENT ET PRÉPARATION DES DONNÉES ---
try:
    df_restaurants = pd.read_csv('restaurants.csv')
    df_menus = pd.read_csv('restaurant-menus.csv')
    df_restaurants.dropna(subset=['full_address', 'name'], inplace=True)
    df_menus.dropna(subset=['name'], inplace=True)
    print("Fichiers CSV chargés avec succès !")
except (FileNotFoundError, KeyError) as e:
    print(f"Erreur lors du chargement des CSV ({e}). Utilisation de données par défaut.")
    df_restaurants = None
# --- FIN DE LA PARTIE ---

# 1. Se connecter au serveur Redis
try:
    r = redis.Redis(decode_responses=True)
    r.ping()
    print("Connecté à Redis avec succès !")
except redis.exceptions.ConnectionError as e:
    print(f"Erreur de connexion à Redis : {e}")
    exit()

# 2. Définir le nom du canal
canal = "nouvelles_courses"

# 3. Créer une offre de course
if df_restaurants is not None and not df_restaurants.empty:
    restaurant_aleatoire = df_restaurants.sample(n=1).iloc[0]
    menu_item_aleatoire = df_menus.sample(n=1).iloc[0]
    
    offre = {
        "id_course": f"course_{int(time.time())}",
        "restaurant": restaurant_aleatoire['name'],
        "adresse_retrait": restaurant_aleatoire['full_address'],
        "adresse_livraison": f"Livraison pour : 34 BIS Rue Pierre Quemener, 93150 Le Blanc Mesnil",
        "retribution": round(random.uniform(4.5, 12.0), 2),
        "statut": "en_attente_de_livreur",
        "livreurs_interesses": [],
        "livreur_attribue": None
    }
else:
    offre = { "id_course": f"course_{int(time.time())}", "restaurant": "Le Pacha", "adresse_retrait": "57 Av. de la Division Leclerc, 93350 Le Bourget", "adresse_livraison": "34 Rue Pierre Quemener, 93150 Le Blanc-Mesnil", "retribution": 13.0, "statut": "en_attente_de_livreur", "livreurs_interesses": [], "livreur_attribue": None }

# 4. Convertir et publier le message
message_json = json.dumps(offre)
r.publish(canal, message_json)

print(f"\nAnnonce (avec adresse de retrait) publiée sur le canal '{canal}':")
print(json.dumps(offre, indent=4))
