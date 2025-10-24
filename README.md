# 🛵 Système de Livraison Redis - Version Finale

## 🎯 Fonctionnalités Principales

✅ **Choix manuel des livreurs** - Chaque livreur décide s'il accepte ou refuse  
✅ **Sélection manuelle du manager** - Le manager choisit quel livreur sélectionner  
✅ **Interface utilisateur améliorée** - Mise en page claire et colorée  
✅ **Code simplifié** - Niveau étudiant BUT3, facile à comprendre  
✅ **Données réelles** - 5000+ restaurants de Birmingham, AL  

## 🚀 Utilisation

### 1. Démarrer Redis
```bash
redis-server
```

### 2. Terminal 1 - Manager
```bash
cd Redis/
python3 manager_redis.py
```
- Tapez `a` pour créer une annonce
- Choisissez manuellement le livreur (1, 2, 3...) ou `a` pour auto
- Tapez `s` pour voir les statistiques

### 3. Terminal 2, 3, 4... - Livreurs
```bash
cd Redis/
python3 livreur_redis.py
```
- Entrez votre nom de livreur
- Répondez `o` (oui) ou `n` (non) aux annonces
- Tapez `s` pour voir vos statistiques

## 🎮 Exemple de Session

### Manager
```
[Manager] > a

============================================================
📢 NOUVELLE ANNONCE CRÉÉE !
============================================================
🆔 ID: 8aa5278a...
🏪 Restaurant: Bay View
📍 Adresse: 123 Main St, Birmingham, AL
🚗 Distance: 3.08 km
💰 Compensation: 5.04€
🍽️  Items: 3 articles
💵 Total commande: 25.50€
============================================================

📨 Réponse reçue de lasry: ❌ Pas intéressé
📨 Réponse reçue de michael: ✅ Intéressé

============================================================
📋 LIVREURS INTÉRESSÉS POUR L'ANNONCE
============================================================
🏪 Restaurant: Bay View
💰 Compensation: 5.04€
🚗 Distance: 3.08 km
============================================================
1. michael (ID: fbda668e...)
   ⏱️  Temps d'arrivée estimé: 6 min
============================================================

🎯 Choisissez un livreur (1-1) ou 'a' pour auto: 1

🎯 Livreur sélectionné: michael

📢 ENVOI DES NOTIFICATIONS...
==================================================
📤 michael: ✅ SÉLECTIONNÉ
==================================================
✅ Toutes les notifications ont été envoyées !
```

### Livreur
```
[lasry] > 

============================================================
📢 NOUVELLE ANNONCE REÇUE !
============================================================
🏪 Restaurant: Bay View
📍 Adresse: 123 Main St, Birmingham, AL
🚗 Distance: 3.08 km
💰 Compensation: 5.04€
🍽️  Items: 3 articles
============================================================

🤔 lasry, êtes-vous intéressé par cette livraison ? (o/n): n
❌ lasry refuse cette livraison
📤 lasry a envoyé sa réponse: ❌ Pas intéressé
```

## 🔧 Architecture Simplifiée

```
Manager (manager_redis.py)
    ↓ Publie annonce
Redis Pub/Sub (order:announcement)
    ↓ Distribue aux livreurs
Livreurs (livreur_redis.py)
    ↓ Répondent manuellement
Redis Pub/Sub (delivery:response)
    ↓ Retourne au manager
Manager choisit manuellement
    ↓ Notifie tous les livreurs
Redis Pub/Sub (delivery:notification)
```

## 📊 Statistiques

### Manager
- Nombre d'annonces actives
- Nombre de réponses par annonce
- Détails des restaurants

### Livreur
- Annonces reçues
- Réponses envoyées
- Sélections reçues
- Gains totaux
- Taux de sélection

## 🎯 Avantages de cette Version

1. **Interactivité** - Choix manuels pour plus de réalisme
2. **Simplicité** - Code accessible niveau BUT3
3. **Beauté** - Interface claire avec emojis et bordures
4. **Fonctionnalité** - Système complet et opérationnel
5. **Données réelles** - Restaurants et menus de Birmingham
6. **Flexibilité** - Sélection manuelle ou automatique

## 🚧 Commandes

### Manager
- `a` - Créer une nouvelle annonce
- `s` - Afficher les statistiques
- `q` - Quitter

### Livreur
- `o/n` - Accepter/refuser une annonce
- `s` - Afficher les statistiques
- `q` - Quitter

## 🎉 Prêt à Utiliser !

Le système est maintenant **parfaitement fonctionnel** avec :
- ✅ Choix manuels des livreurs
- ✅ Sélection manuelle du manager
- ✅ Interface utilisateur améliorée
- ✅ Code simplifié et commenté
- ✅ Compatible Python 3.8+

**Démarrez Redis et lancez les programmes !** 🚀
