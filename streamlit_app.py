#!/usr/bin/env python3
"""
Interface Streamlit pour le Système de Livraison Redis
Interface web unifiée - Manager et Livreurs sur la même page
Réutilise les classes existantes manager_redis.py et livreur_redis.py
"""
import streamlit as st
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# Importer nos classes existantes
from manager_redis import DeliveryManager
from livreur_redis import DeliveryPerson

# Configuration de la page
st.set_page_config(
    page_title="🛵 Système de Livraison Redis",
    page_icon="🛵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 2rem;
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .success-card {
        border-left: 5px solid #4ECDC4;
    }
    .warning-card {
        border-left: 5px solid #FF6B6B;
    }
    .info-card {
        border-left: 5px solid #45B7D1;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitDeliverySystem:
    """Système de livraison avec interface Streamlit unifiée"""
    
    def __init__(self):
        # Initialiser les sessions
        if 'manager' not in st.session_state:
            st.session_state.manager = None
        if 'delivery_persons' not in st.session_state:
            st.session_state.delivery_persons = {}
        if 'pending_announcements' not in st.session_state:
            st.session_state.pending_announcements = {}
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
    
    def init_manager(self):
        """Initialise le manager"""
        if st.session_state.manager is None:
            try:
                st.session_state.manager = DeliveryManager()
                st.session_state.manager.start()
                return True
            except Exception as e:
                st.error(f"Erreur lors de l'initialisation du manager: {e}")
                return False
        return True
    
    def add_delivery_person(self, name: str):
        """Ajoute un livreur"""
        if name in [dp.name for dp in st.session_state.delivery_persons.values()]:
            return False
        
        try:
            delivery_person = DeliveryPerson(str(uuid.uuid4()), name)
            delivery_person.start()
            st.session_state.delivery_persons[name] = delivery_person
            return True
        except Exception as e:
            st.error(f"Erreur lors de l'ajout du livreur: {e}")
            return False
    
    def remove_delivery_person(self, name: str):
        """Supprime un livreur"""
        if name in st.session_state.delivery_persons:
            delivery_person = st.session_state.delivery_persons[name]
            delivery_person.stop()
            del st.session_state.delivery_persons[name]
            return True
        return False

def main():
    """Fonction principale de l'application Streamlit"""
    
    # En-tête principal
    st.markdown("""
    <div class="main-header">
        <h1>🛵 Système de Livraison Redis Pub/Sub</h1>
        <p>Interface unifiée - Manager et Livreurs sur la même page</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialiser le système
    system = StreamlitDeliverySystem()
    
    # Vérifier la connexion Redis
    try:
        if system.init_manager():
            st.success("✅ Connexion Redis active - Manager initialisé")
        else:
            st.error("❌ Connexion Redis échouée - Démarrez Redis avec: redis-server")
            return
    except Exception as e:
        st.error(f"❌ Erreur de connexion: {e}")
        return
    
    # Interface unifiée - Manager et Livreurs côte à côte
    show_unified_interface(system)

def show_unified_interface(system):
    """Interface unifiée - Manager et Livreurs sur la même page"""
    
    # Créer deux colonnes principales
    col1, col2 = st.columns([1, 1])
    
    with col1:
        show_manager_section(system)
    
    with col2:
        show_delivery_section(system)
    
    # Section monitoring en bas
    st.markdown("---")
    show_monitoring_section(system)

def show_manager_section(system):
    """Section Manager"""
    st.markdown("""
    <div class="card info-card">
        <h3>👨‍💼 Manager</h3>
    </div>
    """, unsafe_allow_html=True)
    
    manager = st.session_state.manager
    
    # Créer une annonce
    st.subheader("📢 Créer une annonce")
    if st.button("🎲 Générer une commande aléatoire", type="primary", key="create_announcement"):
        try:
            announcement_id = manager.create_and_publish_announcement()
            st.success(f"✅ Annonce créée et publiée ! ID: {announcement_id[:8]}...")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur: {e}")
    
    # Annonces actives
    st.subheader("📋 Annonces actives")
    if manager.active_announcements:
        for ann_id, ann in manager.active_announcements.items():
            responses = manager.pending_responses.get(ann_id, [])
            interested = [r for r in responses if r.get('is_interested', False)]
            
            with st.expander(f"🏪 {ann['order']['restaurant']['name']} - {len(interested)} intéressé(s)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    **Restaurant:** {ann['order']['restaurant']['name']}  
                    **Distance:** {ann['estimated_distance']} km  
                    **Compensation:** {ann['compensation']}€
                    """)
                
                with col2:
                    st.markdown(f"""
                    **Réponses:** {len(responses)}  
                    **Intéressés:** {len(interested)}  
                    **ID:** {ann_id[:8]}...
                    """)
                
                # Afficher les livreurs intéressés
                if interested:
                    st.markdown("**Livreurs intéressés:**")
                    for i, response in enumerate(interested, 1):
                        st.write(f"{i}. {response['delivery_person_name']}")
                        if response.get('estimated_arrival_time'):
                            st.write(f"   ⏱️ Temps d'arrivée: {response['estimated_arrival_time']} min")
                    
                    # Sélection manuelle
                    st.markdown("**Sélection manuelle:**")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"🎯 Sélectionner {interested[0]['delivery_person_name']}", key=f"select_first_{ann_id}"):
                            # Sélectionner le premier
                            selected = interested[0]
                            _process_selection(manager, ann_id, selected, "Sélection manuelle (premier)")
                            st.rerun()
                    
                    with col2:
                        if len(interested) > 1 and st.button(f"🎯 Sélectionner {interested[1]['delivery_person_name']}", key=f"select_second_{ann_id}"):
                            # Sélectionner le deuxième
                            selected = interested[1]
                            _process_selection(manager, ann_id, selected, "Sélection manuelle (deuxième)")
                            st.rerun()
                    
                    # Sélection automatique
                    if st.button("🤖 Sélection automatique", key=f"auto_select_{ann_id}"):
                        selected = interested[0]  # Premier arrivé
                        _process_selection(manager, ann_id, selected, "Sélection automatique")
                        st.rerun()
                else:
                    st.info("Aucun livreur intéressé pour le moment")
    else:
        st.info("Aucune annonce active")
    
    # Statistiques du manager
    st.subheader("📊 Statistiques")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Annonces actives", len(manager.active_announcements))
    with col2:
        total_responses = sum(len(responses) for responses in manager.pending_responses.values())
        st.metric("Réponses totales", total_responses)

def show_delivery_section(system):
    """Section Livreurs"""
    st.markdown("""
    <div class="card success-card">
        <h3>🛵 Livreurs</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Ajouter un livreur
    st.subheader("👤 Ajouter un livreur")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_delivery_name = st.text_input("Nom du livreur:", placeholder="Ex: Alex Martin", key="new_delivery_name")
    with col2:
        if st.button("➕ Ajouter", type="primary"):
            if new_delivery_name:
                if system.add_delivery_person(new_delivery_name):
                    st.success(f"✅ Livreur {new_delivery_name} ajouté!")
                    st.rerun()
                else:
                    st.error("❌ Nom déjà utilisé ou erreur")
            else:
                st.error("❌ Veuillez entrer un nom")
    
    # Livreurs actifs
    st.subheader("👥 Livreurs actifs")
    if st.session_state.delivery_persons:
        for name, delivery_person in st.session_state.delivery_persons.items():
            with st.expander(f"🛵 {name}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Annonces reçues", delivery_person.stats['announcements_received'])
                with col2:
                    st.metric("Réponses envoyées", delivery_person.stats['responses_sent'])
                with col3:
                    st.metric("Sélections reçues", delivery_person.stats['selections_received'])
                
                st.metric("💰 Gains totaux", f"{delivery_person.stats['total_earnings']:.2f}€")
                
                # Répondre aux annonces en attente
                if delivery_person.pending_announcements:
                    st.markdown("**Annonces en attente de réponse:**")
                    for announcement in delivery_person.pending_announcements:
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"🏪 {announcement['order']['restaurant']['name']} - {announcement['compensation']}€")
                        with col2:
                            if st.button("✅ Accepter", key=f"accept_{name}_{announcement['announcement_id']}"):
                                _send_delivery_response(delivery_person, announcement, True)
                                st.rerun()
                        with col3:
                            if st.button("❌ Refuser", key=f"refuse_{name}_{announcement['announcement_id']}"):
                                _send_delivery_response(delivery_person, announcement, False)
                                st.rerun()
                
                # Bouton supprimer
                if st.button("🗑️ Supprimer", key=f"remove_{name}"):
                    if system.remove_delivery_person(name):
                        st.success(f"✅ Livreur {name} supprimé!")
                        st.rerun()
    else:
        st.info("Aucun livreur ajouté")

def show_monitoring_section(system):
    """Section Monitoring"""
    st.markdown("""
    <div class="card warning-card">
        <h3>📊 Monitoring en Temps Réel</h3>
    </div>
    """, unsafe_allow_html=True)
    
    manager = st.session_state.manager
    
    # Métriques globales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📢 Annonces actives", len(manager.active_announcements))
    
    with col2:
        total_responses = sum(len(responses) for responses in manager.pending_responses.values())
        st.metric("📨 Réponses totales", total_responses)
    
    with col3:
        total_interested = sum(
            len([r for r in responses if r.get('is_interested', False)]) 
            for responses in manager.pending_responses.values()
        )
        st.metric("✅ Livreurs intéressés", total_interested)
    
    with col4:
        total_earnings = sum(
            delivery.stats['total_earnings'] 
            for delivery in st.session_state.delivery_persons.values()
        )
        st.metric("💰 Gains totaux", f"{total_earnings:.2f}€")
    
    # Bouton de rafraîchissement
    if st.button("🔄 Rafraîchir", type="primary"):
        st.rerun()

def _process_selection(manager, announcement_id, selected_response, reason):
    """Traite la sélection d'un livreur"""
    try:
        # Créer la sélection
        selection = {
            'selection_id': str(uuid.uuid4()),
            'announcement_id': announcement_id,
            'selected_delivery_person_id': selected_response['delivery_person_id'],
            'selected_delivery_person_name': selected_response['delivery_person_name'],
            'selection_reason': reason,
            'selected_at': datetime.now().isoformat()
        }
        
        # Publier la sélection
        manager._publish_selection(selection)
        
        # Notifier tous les livreurs
        responses = manager.pending_responses[announcement_id]
        interested_responses = [r for r in responses if r['is_interested']]
        manager._notify_all_delivery_persons(announcement_id, selection, interested_responses)
        
        # Nettoyer les données
        manager._cleanup_announcement(announcement_id)
        
        st.success(f"✅ {selected_response['delivery_person_name']} sélectionné!")
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la sélection: {e}")

def _send_delivery_response(delivery_person, announcement, is_interested):
    """Envoie une réponse de livreur"""
    try:
        # Calculer le temps d'arrivée estimé
        estimated_arrival = None
        if is_interested:
            estimated_arrival = int((announcement['estimated_distance'] / 30.0) * 60)
        
        response = {
            'response_id': str(uuid.uuid4()),
            'delivery_person_id': delivery_person.person_id,
            'delivery_person_name': delivery_person.name,
            'announcement_id': announcement['announcement_id'],
            'is_interested': is_interested,
            'estimated_arrival_time': estimated_arrival,
            'current_location': delivery_person.current_location,
            'response_time': datetime.now().isoformat()
        }
        
        # Envoyer la réponse
        delivery_person._send_response(announcement, is_interested)
        
        # Retirer l'annonce de la queue
        with delivery_person.lock:
            if announcement in delivery_person.pending_announcements:
                delivery_person.pending_announcements.remove(announcement)
        
        status = "accepté" if is_interested else "refusé"
        st.success(f"✅ {delivery_person.name} a {status} l'annonce!")
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'envoi de la réponse: {e}")


if __name__ == "__main__":
    main()
