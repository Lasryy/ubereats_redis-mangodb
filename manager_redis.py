#!/usr/bin/env python3
"""
Manager Redis - Système de livraison de repas
Publie des annonces et sélectionne les livreurs
"""
import redis
import json
import time
import threading
import random
import uuid
import pandas as pd
import math
from datetime import datetime
from typing import List, Dict, Optional, Tuple

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

class DeliveryManager:
    """Manager responsable de la publication d'annonces et de la sélection des livreurs"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        self.active_announcements = {}
        self.pending_responses = {}
        self.running = False
        self.response_listener_thread = None
        
        # Charger les données
        self.restaurants_df = pd.read_csv('restaurants.csv')
        self.menus_df = pd.read_csv('restaurant-menus.csv')
        print(f"✅ Données chargées: {len(self.restaurants_df)} restaurants, {len(self.menus_df)} items de menu")
    
    def start(self):
        """Démarre le manager"""
        print("🚀 Démarrage du DeliveryManager...")
        self.running = True
        
        # Démarrer le thread d'écoute des réponses
        self.response_listener_thread = threading.Thread(target=self._listen_for_responses)
        self.response_listener_thread.daemon = True
        self.response_listener_thread.start()
        
        print("✅ DeliveryManager démarré avec succès")
    
    def stop(self):
        """Arrête le manager"""
        print("🛑 Arrêt du DeliveryManager...")
        self.running = False
        if self.response_listener_thread:
            self.response_listener_thread.join(timeout=5)
        print("✅ DeliveryManager arrêté")
    
    def create_and_publish_announcement(self):
        """Crée et publie une nouvelle annonce de livraison"""
        # Créer une commande aléatoire
        order = self._create_random_order()
        
        # Calculer la distance estimée
        distance = self._calculate_distance(
            order['restaurant']['lat'], order['restaurant']['lng'],
            order['customer_lat'], order['customer_lng']
        )
        
        # Calculer la compensation
        compensation = order['delivery_fee'] + (distance * 0.5)
        
        # Créer l'annonce
        announcement = {
            'announcement_id': str(uuid.uuid4()),
            'order': order,
            'pickup_location': order['restaurant']['address'],
            'delivery_location': order['customer_address'],
            'compensation': round(compensation, 2),
            'estimated_distance': round(distance, 2),
            'created_at': datetime.now().isoformat()
        }
        
        # Stocker l'annonce active
        self.active_announcements[announcement['announcement_id']] = announcement
        self.pending_responses[announcement['announcement_id']] = []
        
        # Afficher l'annonce créée
        print(f"\n{'='*60}")
        print(f"📢 NOUVELLE ANNONCE CRÉÉE !")
        print(f"{'='*60}")
        print(f"🆔 ID: {announcement['announcement_id'][:8]}...")
        print(f"🏪 Restaurant: {order['restaurant']['name']}")
        print(f"📍 Adresse: {order['restaurant']['address']}")
        print(f"🚗 Distance: {distance:.2f} km")
        print(f"💰 Compensation: {compensation:.2f}€")
        print(f"🍽️  Items: {len(order['items'])} articles")
        print(f"💵 Total commande: {order['total_amount']:.2f}€")
        print(f"{'='*60}")
        
        # Publier l'annonce
        self._publish_announcement(announcement)
        
        return announcement['announcement_id']
    
    def _create_random_order(self):
        """Crée une commande aléatoire"""
        # Sélectionner un restaurant aléatoire
        restaurant_data = self.restaurants_df.sample(1).iloc[0]
        
        restaurant = {
            'id': int(restaurant_data['id']),
            'name': restaurant_data['name'],
            'address': restaurant_data['full_address'],
            'lat': float(restaurant_data['lat']),
            'lng': float(restaurant_data['lng']),
            'category': restaurant_data['category'],
            'price_range': restaurant_data['price_range']
        }
        
        # Sélectionner des items du menu
        restaurant_menu = self.menus_df[
            self.menus_df['restaurant_id'] == restaurant['id']
        ].sample(min(3, len(self.menus_df[self.menus_df['restaurant_id'] == restaurant['id']])))
        
        items = []
        total_amount = 0
        for _, item in restaurant_menu.iterrows():
            price_str = str(item['price']).replace('USD', '').strip()
            try:
                price = float(price_str)
            except ValueError:
                price = 0.0
            
            items.append({
                'name': item['name'],
                'category': item['category'],
                'price': price
            })
            total_amount += price
        
        # Générer une localisation client aléatoire
        customer_lat, customer_lng, customer_address = self._generate_customer_location(
            restaurant['lat'], restaurant['lng']
        )
        
        return {
            'order_id': str(uuid.uuid4()),
            'restaurant': restaurant,
            'customer_address': customer_address,
            'customer_lat': customer_lat,
            'customer_lng': customer_lng,
            'items': items,
            'total_amount': total_amount,
            'delivery_fee': 3.50,
            'created_at': datetime.now().isoformat()
        }
    
    def _generate_customer_location(self, restaurant_lat, restaurant_lng, radius_km=5.0):
        """Génère une localisation aléatoire pour un client"""
        # Génération d'un angle et d'une distance aléatoires
        angle = random.uniform(0, 2 * math.pi)
        distance_km = random.uniform(0.5, radius_km)
        
        # Conversion de la distance en degrés
        lat_offset = (distance_km / 111.0) * math.cos(angle)
        lng_offset = (distance_km / (111.0 * math.cos(math.radians(restaurant_lat)))) * math.sin(angle)
        
        customer_lat = restaurant_lat + lat_offset
        customer_lng = restaurant_lng + lng_offset
        
        # Génération d'une adresse fictive
        street_number = random.randint(100, 9999)
        street_names = ["Main St", "Oak Ave", "Pine St", "Elm St", "Maple Ave"]
        street_name = random.choice(street_names)
        customer_address = f"{street_number} {street_name}, Birmingham, AL"
        
        return customer_lat, customer_lng, customer_address
    
    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calcule la distance entre deux points en kilomètres"""
        R = 6371  # Rayon de la Terre en km
        
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _publish_announcement(self, announcement):
        """Publie une annonce sur le channel Redis"""
        try:
            message = json.dumps(announcement, ensure_ascii=False)
            self.redis_client.publish(CHANNELS['ORDER_ANNOUNCEMENT'], message)
            print(f"📡 Annonce publiée sur le channel: {CHANNELS['ORDER_ANNOUNCEMENT']}")
        except Exception as e:
            print(f"❌ Erreur lors de la publication de l'annonce: {e}")
    
    def _listen_for_responses(self):
        """Écoute les réponses des livreurs"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(CHANNELS['DELIVERY_RESPONSE'])
        
        print(f"👂 Écoute des réponses sur le channel: {CHANNELS['DELIVERY_RESPONSE']}")
        
        for message in pubsub.listen():
            if not self.running:
                break
                
            if message['type'] == 'message':
                try:
                    response = json.loads(message['data'])
                    self._process_delivery_response(response)
                except Exception as e:
                    print(f"❌ Erreur lors du traitement de la réponse: {e}")
        
        pubsub.close()
    
    def _process_delivery_response(self, response):
        """Traite une réponse de livreur"""
        announcement_id = response['announcement_id']
        
        if announcement_id not in self.active_announcements:
            print(f"⚠️ Réponse reçue pour une annonce inexistante: {announcement_id}")
            return
        
        # Ajouter la réponse à la liste des réponses en attente
        self.pending_responses[announcement_id].append(response)
        
        status = "✅ Intéressé" if response['is_interested'] else "❌ Pas intéressé"
        print(f"📨 Réponse reçue de {response['delivery_person_name']}: {status}")
        
        # Afficher le nombre total de réponses reçues
        total_responses = len(self.pending_responses[announcement_id])
        interested_count = len([r for r in self.pending_responses[announcement_id] if r['is_interested']])
        print(f"📊 Total: {total_responses} réponse(s) reçue(s) ({interested_count} intéressé(s))")
        
        # Déclencher la sélection après un délai pour laisser le temps aux autres livreurs
        if response['is_interested']:
            # Démarrer un timer pour la sélection (seulement si c'est la première réponse intéressée)
            interested_responses = [r for r in self.pending_responses[announcement_id] if r['is_interested']]
            if len(interested_responses) == 1:  # Première réponse intéressée
                print(f"⏰ Démarrage du timer de sélection (15 secondes)...")
                timer_thread = threading.Timer(15.0, self._consider_selection, args=[announcement_id])
                timer_thread.daemon = True
                timer_thread.start()
    
    def _consider_selection(self, announcement_id):
        """Considère la sélection d'un livreur pour une annonce"""
        announcement = self.active_announcements.get(announcement_id)
        if not announcement:
            return
        
        responses = self.pending_responses[announcement_id]
        interested_responses = [r for r in responses if r['is_interested']]
        
        if not interested_responses:
            print(f"❌ Aucun livreur intéressé pour l'annonce {announcement_id[:8]}...")
            return
        
        print(f"⏰ Timer de sélection déclenché - Traitement des réponses...")
        final_interested = interested_responses
        
        # Afficher les livreurs intéressés et laisser le manager choisir
        print(f"\n{'='*60}")
        print(f"📋 LIVREURS INTÉRESSÉS POUR L'ANNONCE")
        print(f"{'='*60}")
        print(f"🏪 Restaurant: {announcement['order']['restaurant']['name']}")
        print(f"💰 Compensation: {announcement['compensation']}€")
        print(f"🚗 Distance: {announcement['estimated_distance']} km")
        print(f"{'='*60}")
        
        for i, response in enumerate(final_interested, 1):
            print(f"{i}. {response['delivery_person_name']} (ID: {response['delivery_person_id'][:8]}...)")
            if response.get('estimated_arrival_time'):
                print(f"   ⏱️  Temps d'arrivée estimé: {response['estimated_arrival_time']} min")
        
        print(f"{'='*60}")
        
        # Demander au manager de choisir
        while True:
            try:
                choice = input(f"🎯 Choisissez un livreur (1-{len(final_interested)}) ou 'a' pour auto: ").strip().lower()
                
                if choice == 'a':
                    # Sélection automatique (premier arrivé)
                    selected_response = final_interested[0]
                    selection_reason = "Sélection automatique (premier arrivé)"
                    break
                else:
                    try:
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(final_interested):
                            selected_response = final_interested[choice_num - 1]
                            selection_reason = f"Sélection manuelle par le manager"
                            break
                        else:
                            print(f"❌ Veuillez choisir un nombre entre 1 et {len(final_interested)}")
                    except ValueError:
                        print(f"❌ Veuillez entrer un nombre valide ou 'a' pour auto")
            except KeyboardInterrupt:
                print("\n👋 Au revoir!")
                return
        
        # Créer la sélection
        selection = {
            'selection_id': str(uuid.uuid4()),
            'announcement_id': announcement_id,
            'selected_delivery_person_id': selected_response['delivery_person_id'],
            'selected_delivery_person_name': selected_response['delivery_person_name'],
            'selection_reason': selection_reason,
            'selected_at': datetime.now().isoformat()
        }
        
        # Publier la sélection
        self._publish_selection(selection)
        
        # Notifier tous les livreurs
        self._notify_all_delivery_persons(announcement_id, selection, final_interested)
        
        # Nettoyer les données
        self._cleanup_announcement(announcement_id)
        
        print(f"🎯 Livreur sélectionné: {selected_response['delivery_person_name']}")
    
    def _publish_selection(self, selection):
        """Publie la sélection d'un livreur"""
        try:
            message = json.dumps(selection, ensure_ascii=False)
            self.redis_client.publish(CHANNELS['DELIVERY_SELECTION'], message)
            print(f"📡 Sélection publiée sur le channel: {CHANNELS['DELIVERY_SELECTION']}")
        except Exception as e:
            print(f"❌ Erreur lors de la publication de la sélection: {e}")
    
    def _notify_all_delivery_persons(self, announcement_id, selection, interested_responses):
        """Notifie tous les livreurs du résultat de la sélection"""
        print(f"\n📢 ENVOI DES NOTIFICATIONS...")
        print(f"{'='*50}")
        
        for response in interested_responses:
            is_selected = response['delivery_person_id'] == selection['selected_delivery_person_id']
            
            notification = {
                'announcement_id': announcement_id,
                'delivery_person_id': response['delivery_person_id'],
                'delivery_person_name': response['delivery_person_name'],
                'is_selected': is_selected,
                'selected_delivery_person_name': selection['selected_delivery_person_name'] if is_selected else None,
                'notification_time': datetime.now().isoformat()
            }
            
            try:
                message = json.dumps(notification, ensure_ascii=False)
                self.redis_client.publish(CHANNELS['DELIVERY_NOTIFICATION'], message)
                
                status = "✅ SÉLECTIONNÉ" if is_selected else "❌ Non sélectionné"
                print(f"📤 {response['delivery_person_name']}: {status}")
                
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi de la notification: {e}")
        
        print(f"{'='*50}")
        print(f"✅ Toutes les notifications ont été envoyées !")
    
    def _cleanup_announcement(self, announcement_id):
        """Nettoie les données d'une annonce terminée"""
        if announcement_id in self.active_announcements:
            del self.active_announcements[announcement_id]
        if announcement_id in self.pending_responses:
            del self.pending_responses[announcement_id]
    
    def _force_selection(self):
        """Force la sélection pour une annonce active"""
        if not self.active_announcements:
            print("❌ Aucune annonce active pour forcer la sélection")
            return
        
        print(f"\n{'='*50}")
        print(f"🚀 FORCER LA SÉLECTION")
        print(f"{'='*50}")
        
        # Afficher les annonces actives
        for i, (ann_id, ann) in enumerate(self.active_announcements.items(), 1):
            responses = len(self.pending_responses.get(ann_id, []))
            interested = len([r for r in self.pending_responses.get(ann_id, []) if r['is_interested']])
            restaurant = ann['order']['restaurant']['name']
            print(f"{i}. {ann_id[:8]}... ({restaurant}): {responses} réponse(s), {interested} intéressé(s)")
        
        print(f"{'='*50}")
        
        # Demander quelle annonce traiter
        while True:
            try:
                choice = input(f"🎯 Choisissez une annonce (1-{len(self.active_announcements)}) ou 'a' pour toutes: ").strip().lower()
                
                if choice == 'a':
                    # Traiter toutes les annonces
                    for ann_id in list(self.active_announcements.keys()):
                        self._consider_selection(ann_id)
                    break
                else:
                    try:
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(self.active_announcements):
                            ann_id = list(self.active_announcements.keys())[choice_num - 1]
                            self._consider_selection(ann_id)
                            break
                        else:
                            print(f"❌ Veuillez choisir un nombre entre 1 et {len(self.active_announcements)}")
                    except ValueError:
                        print(f"❌ Veuillez entrer un nombre valide ou 'a' pour toutes")
            except KeyboardInterrupt:
                print("\n👋 Au revoir!")
                return


def main():
    """Fonction principale"""
    print("🛵 MANAGER REDIS - SYSTÈME DE LIVRAISON")
    print("=" * 50)
    
    try:
        # Créer le manager
        manager = DeliveryManager()
        manager.start()
        
        print(f"\n{'='*50}")
        print(f"🎮 COMMANDES DISPONIBLES")
        print(f"{'='*50}")
        print("  'a' - Créer une nouvelle annonce")
        print("  's' - Afficher les statistiques")
        print("  'f' - Forcer la sélection pour une annonce")
        print("  'q' - Quitter le programme")
        print(f"{'='*50}")
        print(f"💡 Créez une annonce et choisissez manuellement le livreur !")
        print(f"{'='*50}")
        
        while True:
            try:
                command = input(f"\n[Manager] > ").strip().lower()
                
                if command == 'a':
                    manager.create_and_publish_announcement()
                
                elif command == 's':
                    print(f"\n{'='*50}")
                    print(f"📊 STATISTIQUES ACTUELLES")
                    print(f"{'='*50}")
                    print(f"📢 Annonces actives: {len(manager.active_announcements)}")
                    if manager.active_announcements:
                        for ann_id, ann in manager.active_announcements.items():
                            responses = len(manager.pending_responses.get(ann_id, []))
                            restaurant = ann['order']['restaurant']['name']
                            print(f"   - {ann_id[:8]}... ({restaurant}): {responses} réponse(s)")
                    else:
                        print("   Aucune annonce active")
                    print(f"{'='*50}")
                
                elif command == 'f':
                    manager._force_selection()
                
                elif command == 'q':
                    print("👋 Au revoir!")
                    break
                
                else:
                    print("❌ Commande inconnue. Utilisez 'a', 's', 'f' ou 'q'")
                    
            except KeyboardInterrupt:
                print("\n👋 Au revoir!")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
    
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
    finally:
        if 'manager' in locals():
            manager.stop()


if __name__ == "__main__":
    main()
