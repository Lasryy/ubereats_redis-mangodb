# livreur_redis.py
import redis
import json

# 1. Se connecter au serveur Redis
try:
    r = redis.Redis(decode_responses=True)
    r.ping()
    print("Connecté à Redis avec succès !")
except redis.exceptions.ConnectionError as e:
    print(f"Erreur de connexion à Redis : {e}")
    exit()

# 2. Définir le nom du canal à écouter
canal = "nouvelles_courses"

# 3. Créer un objet PubSub et s'abonner au canal
p = r.pubsub()
p.subscribe(canal)

print(f"\nLivreur en attente de courses sur le canal '{canal}'...")
print("(Utilisez Ctrl+C pour arrêter)")

# 4. Boucle infinie pour écouter les messages
try:
    for message in p.listen():
        # On ignore les messages de confirmation d'abonnement
        if message['type'] == 'message':
            # On récupère les données et on les convertit depuis le JSON
            data = json.loads(message['data'])
            
            print("\n[!] Nouvelle course disponible !")
            print(f"    ID: {data.get('id_course')}")
            print(f"    Restaurant: {data.get('restaurant')}")
            print(f"    Adresse: {data.get('adresse_livraison')}")
            print(f"    Rétribution: {data.get('retribution')} $")

except KeyboardInterrupt:
    print("\nArrêt du programme livreur.")
finally:
    p.close()
