#!/usr/bin/env python3
"""
Livreur Redis - Système de livraison de repas
Écoute les annonces et manifeste son intérêt
"""
import redis
import json
import time
import threading
import random
import uuid
import math
from datetime import datetime
from typing import Dict, Optional

# Configuration Redis
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Channels Redis
CHANNELS = {
    'ORDER_ANNOUNCEMENT': 'order:announcement',
    'DELIVERY_RESPONSE': 'delivery:response',
    'DELIVERY_SELECTION': 'delivery:selection',
    'DELIVERY_NOTIFICATION': 'delivery:notification'
}

class DeliveryPerson:
    """Classe représentant un livreur individuel"""
    
    def __init__(self, person_id: str, name: str, current_location: str = "Birmingham, AL"):
        self.person_id = person_id
        self.name = name
        self.current_location = current_location
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        self.running = False
        
        # Threads pour écouter les annonces et notifications
        self.announcement_listener_thread = None
        self.notification_listener_thread = None
        
        # Queue pour les annonces en attente de réponse
        self.pending_announcements = []
        self.lock = threading.Lock()
        
        # Statistiques
        self.stats = {
            'announcements_received': 0,
            'responses_sent': 0,
            'selections_received': 0,
            'total_earnings': 0.0
        }
        
        # Comportement du livreur
        self.interest_probability = random.uniform(0.3, 0.9)  # Probabilité d'être intéressé
        self.response_delay_range = (1, 5)  # Délai de réponse en secondes
        
    def start(self):
        """Démarre le livreur"""
        print(f"🚀 Démarrage du livreur {self.name} (ID: {self.person_id})...")
        self.running = True
        
        # Démarrer les threads d'écoute
        self.announcement_listener_thread = threading.Thread(target=self._listen_for_announcements)
        self.announcement_listener_thread.daemon = True
        self.announcement_listener_thread.start()
        
        self.notification_listener_thread = threading.Thread(target=self._listen_for_notifications)
        self.notification_listener_thread.daemon = True
        self.notification_listener_thread.start()
        
        print(f"✅ Livreur {self.name} démarré avec succès")
        print(f"   Probabilité d'intérêt: {self.interest_probability:.2f}")
    
    def stop(self):
        """Arrête le livreur"""
        print(f"🛑 Arrêt du livreur {self.name}...")
        self.running = False
        
        if self.announcement_listener_thread:
            self.announcement_listener_thread.join(timeout=5)
        if self.notification_listener_thread:
            self.notification_listener_thread.join(timeout=5)
        
        print(f"✅ Livreur {self.name} arrêté")
    
    def _listen_for_announcements(self):
        """Écoute les annonces de livraison"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(CHANNELS['ORDER_ANNOUNCEMENT'])
        
        print(f"👂 {self.name} écoute les annonces sur: {CHANNELS['ORDER_ANNOUNCEMENT']}")
        
        for message in pubsub.listen():
            if not self.running:
                break
                
            if message['type'] == 'message':
                try:
                    announcement = json.loads(message['data'])
                    self._process_announcement(announcement)
                except Exception as e:
                    print(f"❌ Erreur lors du traitement de l'annonce par {self.name}: {e}")
        
        pubsub.close()
    
    def _listen_for_notifications(self):
        """Écoute les notifications de sélection"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(CHANNELS['DELIVERY_NOTIFICATION'])
        
        print(f"👂 {self.name} écoute les notifications sur: {CHANNELS['DELIVERY_NOTIFICATION']}")
        
        for message in pubsub.listen():
            if not self.running:
                break
                
            if message['type'] == 'message':
                try:
                    notification = json.loads(message['data'])
                    
                    # Vérifier si la notification nous concerne
                    if notification.get('delivery_person_id') == self.person_id:
                        self._process_notification(notification)
                    
                except Exception as e:
                    print(f"❌ Erreur lors du traitement de la notification par {self.name}: {e}")
        
        pubsub.close()
    
    def _process_announcement(self, announcement):
        """Traite une annonce de livraison"""
        self.stats['announcements_received'] += 1
        
        # Ajouter l'annonce à la queue
        with self.lock:
            self.pending_announcements.append(announcement)
        
        print(f"\n{'='*60}")
        print(f"📢 NOUVELLE ANNONCE REÇUE !")
        print(f"{'='*60}")
        print(f"🏪 Restaurant: {announcement['order']['restaurant']['name']}")
        print(f"📍 Adresse: {announcement['order']['restaurant']['address']}")
        print(f"🚗 Distance: {announcement['estimated_distance']} km")
        print(f"💰 Compensation: {announcement['compensation']}€")
        print(f"🍽️  Items: {len(announcement['order']['items'])} articles")
        print(f"{'='*60}")
        print(f"💡 Tapez 'r' pour répondre à cette annonce")
        print(f"{'='*60}")
    
    def _respond_to_announcement(self):
        """Permet au livreur de répondre à une annonce en attente"""
        with self.lock:
            if not self.pending_announcements:
                print("❌ Aucune annonce en attente de réponse")
                return
            
            # Prendre la première annonce en attente
            announcement = self.pending_announcements.pop(0)
        
        print(f"\n{'='*60}")
        print(f"📋 ANNONCE EN ATTENTE DE RÉPONSE")
        print(f"{'='*60}")
        print(f"🏪 Restaurant: {announcement['order']['restaurant']['name']}")
        print(f"📍 Adresse: {announcement['order']['restaurant']['address']}")
        print(f"🚗 Distance: {announcement['estimated_distance']} km")
        print(f"💰 Compensation: {announcement['compensation']}€")
        print(f"🍽️  Items: {len(announcement['order']['items'])} articles")
        print(f"{'='*60}")
        
        # Demander à l'utilisateur s'il est intéressé
        while True:
            try:
                choice = input(f"🤔 {self.name}, êtes-vous intéressé par cette livraison ? (o/n): ").strip().lower()
                if choice in ['o', 'oui', 'y', 'yes']:
                    is_interested = True
                    break
                elif choice in ['n', 'non', 'no']:
                    is_interested = False
                    break
                else:
                    print("❌ Veuillez répondre 'o' pour oui ou 'n' pour non")
            except KeyboardInterrupt:
                print("\n👋 Au revoir!")
                return
        
        if is_interested:
            print(f"✅ {self.name} accepte cette livraison !")
            self._send_response(announcement, is_interested=True)
        else:
            print(f"❌ {self.name} refuse cette livraison")
            self._send_response(announcement, is_interested=False)
    
    def _decide_interest(self, announcement):
        """Décide si le livreur est intéressé par une annonce"""
        # Facteurs de décision:
        # 1. Probabilité de base
        # 2. Distance (plus c'est loin, moins on est intéressé)
        # 3. Compensation (plus c'est payé, plus on est intéressé)
        
        base_interest = self.interest_probability
        
        # Ajustement basé sur la distance (max 10km)
        distance_factor = max(0.1, 1.0 - (announcement['estimated_distance'] / 10.0))
        
        # Ajustement basé sur la compensation (min 3€, max 15€)
        compensation_factor = min(1.5, announcement['compensation'] / 8.0)
        
        # Calcul de la probabilité finale
        final_probability = base_interest * distance_factor * compensation_factor
        
        return random.random() < final_probability
    
    def _send_response(self, announcement, is_interested):
        """Envoie une réponse à une annonce"""
        # Calculer le temps d'arrivée estimé
        estimated_arrival = None
        if is_interested:
            # Estimation basée sur la distance (vitesse moyenne 30 km/h)
            estimated_arrival = int((announcement['estimated_distance'] / 30.0) * 60)  # en minutes
        
        response = {
            'response_id': str(uuid.uuid4()),
            'delivery_person_id': self.person_id,
            'delivery_person_name': self.name,
            'announcement_id': announcement['announcement_id'],
            'is_interested': is_interested,
            'estimated_arrival_time': estimated_arrival,
            'current_location': self.current_location,
            'response_time': datetime.now().isoformat()
        }
        
        try:
            message = json.dumps(response, ensure_ascii=False)
            self.redis_client.publish(CHANNELS['DELIVERY_RESPONSE'], message)
            
            self.stats['responses_sent'] += 1
            
            status = "✅ Intéressé" if is_interested else "❌ Pas intéressé"
            print(f"📤 {self.name} a envoyé sa réponse: {status}")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi de la réponse par {self.name}: {e}")
    
    def _process_notification(self, notification):
        """Traite une notification de sélection"""
        self.stats['selections_received'] += 1
        
        is_selected = notification.get('is_selected', False)
        
        print(f"\n{'='*60}")
        if is_selected:
            print(f"🎉 Félicitations {self.name.upper()} !")
            print(f"🎯 Vous avez été sélectionné pour cette livraison !")
            # Simuler l'ajout des gains
            self.stats['total_earnings'] += 5.0  # Montant fictif
        else:
            selected_person = notification.get('selected_delivery_person_name', 'Inconnu')
            print(f"😔 DÉSOLÉ {self.name}")
            print(f"❌ Vous n'avez pas été sélectionné")
        print(f"{'='*60}")
    
    def get_stats(self):
        """Retourne les statistiques du livreur"""
        return {
            'person_id': self.person_id,
            'name': self.name,
            'current_location': self.current_location,
            'stats': self.stats.copy(),
            'interest_probability': self.interest_probability
        }
    
    def print_stats(self):
        """Affiche les statistiques du livreur"""
        print(f"\n{'='*50}")
        print(f"📊 STATISTIQUES DE {self.name.upper()}")
        print(f"{'='*50}")
        print(f"📨 Annonces reçues: {self.stats['announcements_received']}")
        print(f"📤 Réponses envoyées: {self.stats['responses_sent']}")
        print(f"🏆 Sélections reçues: {self.stats['selections_received']}")
        print(f"💰 Gains totaux: {self.stats['total_earnings']:.2f}€")
        print(f"🎯 Taux de sélection: {(self.stats['selections_received']/max(1,self.stats['responses_sent'])*100):.1f}%")
        print(f"{'='*50}")


def main():
    """Fonction principale"""
    print("🛵 LIVREUR REDIS - SYSTÈME DE LIVRAISON")
    print("=" * 50)
    
    # Demander le nom du livreur
    name = input("👤 Entrez votre nom de livreur: ").strip()
    if not name:
        name = f"Livreur_{random.randint(1000, 9999)}"
    
    try:
        # Créer le livreur
        delivery_person = DeliveryPerson(str(uuid.uuid4()), name)
        delivery_person.start()
        
        print(f"\n{'='*50}")
        print(f"🎮 COMMANDES DISPONIBLES")
        print(f"{'='*50}")
        print("  'r' - Répondre à une annonce en attente")
        print("  's' - Afficher mes statistiques")
        print("  'q' - Quitter le programme")
        print(f"{'='*50}")
        print(f"👤 Livreur {name} en attente d'annonces...")
        print(f"💡 Vous recevrez des annonces automatiquement !")
        print(f"{'='*50}")
        
        while True:
            try:
                command = input(f"\n[{name}] > ").strip().lower()
                
                if command == 'r':
                    delivery_person._respond_to_announcement()
                
                elif command == 's':
                    delivery_person.print_stats()
                
                elif command == 'q':
                    print("👋 Au revoir!")
                    break
                
                else:
                    print("❌ Commande inconnue. Utilisez 'r', 's' ou 'q'")
                    
            except KeyboardInterrupt:
                print("\n👋 Au revoir!")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
    
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
    finally:
        if 'delivery_person' in locals():
            delivery_person.stop()


if __name__ == "__main__":
    main()
