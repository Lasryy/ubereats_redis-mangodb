# corrected_manager_redis.py
import redis
import json
import time
import pandas as pd
import random

# --- PARTIE : CHARGEMENT ET PRÉPARATION DES DONNÉES ---

try:
    # Charger les données depuis les fichiers CSV
    df_restaurants = pd.read_csv('restaurants.csv')
    df_menus = pd.read_csv('restaurant-menus.csv')
    
    # On supprime les lignes avec des valeurs manquantes pour les colonnes qu'on va utiliser
    df_restaurants.dropna(subset=['full_address', 'name'], inplace=True)
    # Ligne corrigée : on utilise 'name' qui est le nom correct de la colonne
    df_menus.dropna(subset=['name'], inplace=True)

    print("Fichiers CSV chargés avec succès !")

except FileNotFoundError:
    print("Erreur : Un ou plusieurs fichiers CSV sont introuvables. Utilisation de données par défaut.")
    df_restaurants = None
except KeyError as e:
    print(f"Erreur de nom de colonne : {e}. Vérifiez que les noms de colonnes dans le script correspondent à vos fichiers.")
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
    # --- PARTIE : SÉLECTION ALÉATOIRE ---
    
    # Choisir un restaurant au hasard
    restaurant_aleatoire = df_restaurants.sample(n=1).iloc[0]
    
    # Choisir un plat au hasard pour simuler une commande
    menu_item_aleatoire = df_menus.sample(n=1).iloc[0]
    
    # Créer l'offre avec les données dynamiques
    offre = {
        "id_course": f"course_{int(time.time())}",
        "restaurant": restaurant_aleatoire['name'],
        # Ligne corrigée : on utilise la colonne 'name' du menu
        "adresse_livraison": f"Livraison pour : {menu_item_aleatoire['name']}",
        "retribution": round(random.uniform(4.5, 12.0), 2)
    }
    # --- FIN DE LA PARTIE ---
else:
    # Données de secours si les fichiers ne sont pas chargés
    offre = {
        "id_course": f"course_{int(time.time())}",
        "restaurant": "Restaurant par Défaut",
        "adresse_livraison": "Adresse par Défaut",
        "retribution": 5.0
    }

# 4. Convertir et publier le message
message_json = json.dumps(offre)
r.publish(canal, message_json)

print(f"\nAnnonce dynamique publiée sur le canal '{canal}':")
print(offre)
