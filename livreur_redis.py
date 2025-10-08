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

# 3. S'abonner au canal
p = r.pubsub()
p.subscribe(canal)

print(f"\nLivreur en attente de courses sur le canal '{canal}'...")
print("(Utilisez Ctrl+C pour arrêter)")

# 4. Boucle pour écouter les messages
try:
    for message in p.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            
            print("\n[!] Nouvelle course disponible !")
            print(f"    ID: {data.get('id_course')}")
            print(f"    Point de retrait: {data.get('restaurant')} - {data.get('adresse_retrait')}")
            print(f"    Destination: {data.get('adresse_livraison')}")
            print(f"    Rétribution: {data.get('retribution')} €")
            print(f"    Statut: {data.get('statut')}")

except KeyboardInterrupt:
    print("\nArrêt du programme livreur.")
finally:
    p.close()
