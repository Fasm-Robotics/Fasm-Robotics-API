from fastapi import FastAPI, HTTPException
from lib import Controller, MotorName

# Initialisation de l'application FastAPI
app = FastAPI()

# Initialisation du contrôleur Arduino (sans connexion initiale)
arduino = None

# État de la connexion
is_connected = False


@app.post("/connect")
async def connect_arduino(port: str = "COM3", baudrate: int = 9600):
    """
    Connecte l'Arduino via le port série avec un port et un baudrate spécifiés.
    """
    global arduino, is_connected
    try:
        if is_connected:
            return {"status": "success", "message": "Arduino déjà connecté."}
        ctrl = Controller(port=port, baudrate=baudrate)
        ctrl.add_motor("3078385E3533", MotorName.SH1)
        ctrl.add_motor("376233523433", MotorName.SH2)
        ctrl.add_motor("376433673433", MotorName.SH3)
        ctrl.init()
        is_connected = True
        return {
            "status": "success",
            "message": f"Connexion à l'Arduino établie sur {port} à {baudrate} bauds.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la connexion : {e}")


@app.post("/disconnect")
async def disconnect_arduino():
    """
    Déconnecte l'Arduino du port série.
    """
    global ctrl, is_connected
    try:
        if not is_connected:
            return {"status": "success", "message": "Arduino déjà déconnecté."}
        ctrl.exit()
        is_connected = False
        return {"status": "success", "message": "Connexion à l'Arduino fermée."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la déconnexion : {e}")


@app.post("/set-angle")
async def set_angle(motor: str, angle: float):
    """
    Met à jour l'angle du moteur "motor".
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        if motor not in MotorName.__members__:
            raise ValueError("Nom de moteur invalide.")
        response = ctrl.get_motor(motor).set_angle(angle)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-angle")
async def get_angle(motor: str):
    """
    Récupère l'angle actuel du moteur "motor".
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        if motor not in MotorName.__members__:
            raise ValueError("Nom de moteur invalide.")
        angle = ctrl.get_motor(motor).get_angle()
        return {"status": "success", "motor": "motor1", "angle": angle}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/reboot")
async def reboot(motor: str = None):
    """
    Redémarre le moteur spécifié ou tous les moteurs.
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        ctrl.reboot(motor)
        return {"status": "success", "message": "Redémarrage effectué."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=5000)
