# 📦 Intégration OpenMediaVault pour Home Assistant

Cette intégration custom Home Assistant expose l’état de vos disques OpenMediaVault (température, capacité totale et disponible) via l’API RPC native d’OMV. Elle s’installe via HACS ou en copiant le dossier `custom_components/openmediavault`.

## ✨ Fonctionnalités
- 🔥 Capteurs de température par disque avec mise à jour automatique.
- 💾 Deux capteurs d’espace (total & disponible) pour chaque disque détecté.
- 📉 Calcul du pourcentage d’occupation à partir de la capacité utilisée.
- 📊 Attributs détaillés : modèle, statut, point de montage, type de FS, tailles en Go (total/disponible/utilisé).
- 🎯 Valeurs recommandées min/max pour un affichage graphique cohérent.

## 🚀 Installation
1. **HACS (recommandé)**  
   - Ajoutez ce dépôt en tant que *Custom Repository* (catégorie *Integration*).  
   - Installez *OpenMediaVault for Home Assistant* depuis HACS puis redémarrez Home Assistant.
2. **Manuel**  
   - Copiez `custom_components/openmediavault` dans le dossier `custom_components/` de votre instance HA.  
   - Redémarrez Home Assistant pour charger l’intégration.

## 🛠 Configuration
1. Dans Home Assistant, ouvrez **Paramètres → Appareils & Services → Ajouter une intégration**.  
2. Cherchez *OpenMediaVault* et renseignez `host`, `username`, `password` (un compte admin OMV).  
3. Les capteurs apparaissent avec le préfixe `sensor.omv_*`. Vérifiez que le compte OMV possède l’accès RPC.

## 📁 Structure du dépôt
```
custom_components/openmediavault/
├── __init__.py        # Coordinator + appels RPC OMV
├── sensor.py          # Entités Home Assistant (température & capacité)
├── config_flow.py     # Formulaire de configuration UI
├── const.py / manifest.json / omv.py
tests/
├── test_const*.py     # Exemples Pytest et unittest
├── test_coordinator_merge.py
```

## 🧪 Tests & développement
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install homeassistant pytest
pytest tests -q
```
