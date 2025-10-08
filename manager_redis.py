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
    
    # Nettoyage des données pour éviter les erreurs
    df_restaurants.dropna(subset=['id', 'full_address', 'name'], inplace=True)
    df_menus.dropna(subset=['restaurant_id', 'name', 'price'], inplace=True)

    # Conversion de la colonne 'price' en numérique, gère les erreurs
    df_menus['price'] = pd.to_numeric(df_menus['price'], errors='coerce')
    df_menus.dropna(subset=['price'], inplace=True)

    print("Fichiers CSV chargés et préparés avec succès !")
except (FileNotFoundError, KeyError) as e:
    print(f"Erreur lors du chargement des CSV ({e}).")
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

# 3. Créer une offre de course (Logique Avancée)
offre = {}
if df_restaurants is not None and not df_restaurants.empty:
    
    panier_valide = False
    # Boucle pour s'assurer qu'on trouve un restaurant avec un menu dans l'autre fichier
    while not panier_valide:
        # Étape 1: Choisir un restaurant au hasard
        restaurant_aleatoire = df_restaurants.sample(n=1).iloc[0]
        restaurant_id = restaurant_aleatoire['id']
        
        # Étape 2: Trouver le menu correspondant à ce restaurant
        menu_du_restaurant = df_menus[df_menus['restaurant_id'] == restaurant_id]
        
        # Si le menu n'est pas vide, on peut créer un panier
        if not menu_du_restaurant.empty:
            panier_valide = True

    # Étape 3: Créer un "panier" avec 1 à 3 plats du menu trouvé
    nombre_plats = random.randint(1, min(3, len(menu_du_restaurant)))
    panier = menu_du_restaurant.sample(n=nombre_plats)
    
    # Étape 4: Calculer le total de la commande
    total_commande = panier['price'].sum()
    
    # Étape 5: Définir la rétribution du livreur (ex: 2.50€ fixe + 10% du total)
    retribution_calculee = 2.50 + (total_commande * 0.10)
    
    # Créer une description de la commande à partir du nom des plats
    description_commande = ", ".join(panier['name'].tolist())
    
    # Étape 6: Construire l'offre finale
    offre = {
        "id_course": f"course_{int(time.time())}",
        "restaurant": restaurant_aleatoire['name'],
        "adresse_retrait": restaurant_aleatoire['full_address'],
        # On garde votre adresse de livraison fixe, mais on ajoute la description
        "adresse_livraison": "34 BIS Rue Pierre Quemener, 93150 Le Blanc Mesnil",
        "description_commande": description_commande,
        "retribution": round(retribution_calculee, 2),
        "statut": "en_attente_de_livreur",
        "livreurs_interesses": [],
        "livreur_attribue": None
    }

# 4. Convertir et publier le message
if offre:
    message_json = json.dumps(offre)
    r.publish(canal, message_json)

    print(f"\nAnnonce (avancée) publiée sur le canal '{canal}':")
    print(json.dumps(offre, indent=4))
else:
    # Ce message s'affiche si la création de l'offre échoue (ex: fichiers CSV vides)
    print("N'a pas pu créer d'offre (problème de données).")
