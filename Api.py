from fastapi import FastAPI, HTTPException
from lib import MotorController

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
        arduino = MotorController(port=port, baudrate=baudrate)
        arduino.connect()
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
    global arduino, is_connected
    try:
        if not is_connected:
            return {"status": "success", "message": "Arduino déjà déconnecté."}
        arduino.disconnect()
        is_connected = False
        return {"status": "success", "message": "Connexion à l'Arduino fermée."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la déconnexion : {e}")


@app.post("/motor1/update")
async def update_motor1(angle: float):
    """
    Met à jour l'angle du moteur 1.
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        response = arduino.update_motor1(angle)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/motor2/update")
async def update_motor2(angle: float):
    """
    Met à jour l'angle du moteur 2.
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        response = arduino.update_motor2(angle)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/motor3/update")
async def update_motor3(angle: float):
    """
    Met à jour l'angle du moteur 3.
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        response = arduino.update_motor3(angle)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/motor1")
async def get_motor1():
    """
    Récupère l'angle actuel du moteur 1.
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        angle = arduino.get_motor1()
        return {"status": "success", "motor": "motor1", "angle": angle}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/motor2")
async def get_motor2():
    """
    Récupère l'angle actuel du moteur 2.
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        angle = arduino.get_motor2()
        return {"status": "success", "motor": "motor2", "angle": angle}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/motor3")
async def get_motor3():
    """
    Récupère l'angle actuel du moteur 3.
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        angle = arduino.get_motor3()
        return {"status": "success", "motor": "motor3", "angle": angle}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset")
async def reset_motors():
    """
    Réinitialise les angles des moteurs.
    """
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        arduino.reset_motors()
        return {"status": "success", "message": "Les moteurs ont été réinitialisés."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
