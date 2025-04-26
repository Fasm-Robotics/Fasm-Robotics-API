# API Robot Arm – Contrôle du bras robotique Arduino

Cette API (développée avec FastAPI) permet de contrôler un bras robotisé piloté par une carte Arduino. Elle expose différentes routes HTTP pour se connecter au bras, déplacer ses moteurs, effectuer des calibrations, etc. Toutes les données d'angle sont exprimées en **degrés**.

## Lancement de l'API

Assurez-vous d'avoir Python 3 installé ainsi que les dépendances nécessaires (`fastapi`, `uvicorn`, etc.). Pour démarrer le serveur de l'API, exécutez la commande suivante :

```bash
uvicorn main:app --reload
