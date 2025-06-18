from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from lib import Controller, MotorName
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Variables globales ---
ctrl: Optional[Controller] = None
is_connected = False

# --- Chemin du URDF ---
current_dir = os.path.dirname(__file__)
urdf_path = os.path.join(current_dir, "robotarm_corrected.urdf")

# --- Modèles Pydantic ---
class ConnectRequest(BaseModel):
    port: str = "COM5"
    baudrate: int = 115200

class SetMotorAngleRequest(BaseModel):
    motor: str
    angle: float

class SetSyncAnglesRequest(BaseModel):
    angles: Dict[str, float]

class MotorStateRequest(BaseModel):
    motor: str

class CalibrateRequest(BaseModel):
    motor: str

class CalibrateSyncRequest(BaseModel):
    motors: List[str]

class PositionInput(BaseModel):
    x: float
    y: float
    z: float

# --- Routes API ---
@app.post("/connect")
async def connect_arduino(req: ConnectRequest):
    global ctrl, is_connected
    try:
        if is_connected:
            return {"status": "success", "message": "Déjà connecté."}
        ctrl = Controller(port=req.port, urdf_path=urdf_path)
        is_connected = True
        return {"status": "success", "message": f"Connecté à {req.port}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/disconnect")
async def disconnect_arduino():
    global ctrl, is_connected
    try:
        if not is_connected:
            return {"status": "success", "message": "Déjà déconnecté."}
        ctrl = None
        is_connected = False
        return {"status": "success", "message": "Déconnecté avec succès."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reverseK")
async def compute_inverse_kinematics(pos: PositionInput):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        angles_deg = ctrl.goto(pos.x, pos.y, pos.z, True)
        return {"status": "success"} + {k.name: v for k, v in angles_deg.items()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/preview-reverseK")
async def compute_inverse_kinematics(pos: PositionInput):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        angles_deg = ctrl.goto(pos.x, pos.y, pos.z, move=False)
        return {"status": "success", **{k.name: v for k, v in angles_deg.items()}}
    except Exception as e:
        print(f"Erreur lors du calcul de la cinématique inverse : {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-motor-angle")
async def set_motor_angle(req: SetMotorAngleRequest):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        if req.motor not in MotorName.__members__:
            raise ValueError("Nom de moteur invalide.")
        motor_enum = MotorName[req.motor]
        ctrl.set_motor_angle(motor_enum, req.angle)
        return {"status": "success", "message": f"{req.motor} déplacé à {req.angle} degrés"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-sync-angles")
async def set_sync_angles(req: SetSyncAnglesRequest):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        angles = {}
        for name, angle in req.angles.items():
            if name not in MotorName.__members__:
                raise ValueError(f"Moteur invalide : {name}")
            angles[MotorName[name]] = angle
        ctrl.set_motors_angles(angles)
        return {"status": "success", "message": "Angles synchronisés."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-motor-angle")
async def get_motor_angle(motor: str = Query(..., description="Nom du moteur (SH1, SH2, SH3, EL1)")):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        if motor not in MotorName.__members__:
            raise ValueError("Nom de moteur invalide.")
        motor_enum = MotorName[motor]
        angles = ctrl.arduino.get_latest_position({motor_enum: 0})
        if angles[motor_enum] is None:
            raise ValueError("Erreur de lecture de la position.")
        return {"status": "success", "angle_degrees": angles[motor_enum]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calibrate")
async def calibrate_motor(req: CalibrateRequest):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        if req.motor not in MotorName.__members__:
            raise ValueError("Nom de moteur invalide.")
        ctrl.calibrate(MotorName[req.motor])
        return {"status": "success", "message": f"Moteur {req.motor} calibré."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calibrate-sync")
async def calibrate_sync(req: CalibrateSyncRequest):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        motors = {MotorName[name]: 0.0 for name in req.motors if name in MotorName.__members__}
        ctrl.arduino.calibrate(motors)
        return {"status": "success", "message": f"Calibration sync réussie pour {', '.join(req.motors)}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-closed-loop")
async def set_closed_loop(req: MotorStateRequest):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        if req.motor not in MotorName.__members__:
            raise ValueError("Nom de moteur invalide.")
        ctrl.arduino.set_closed_loop({MotorName[req.motor]: 0})
        return {"status": "success", "message": f"{req.motor} en boucle fermée."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-idle")
async def set_idle(req: MotorStateRequest):
    if not is_connected:
        raise HTTPException(status_code=400, detail="Arduino non connecté.")
    try:
        if req.motor not in MotorName.__members__:
            raise ValueError("Nom de moteur invalide.")
        ctrl.arduino.set_idle({MotorName[req.motor]: 0})
        return {"status": "success", "message": f"{req.motor} mis en IDLE."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reboot")
async def reboot():
    return {"status": "success", "message": "Reboot fictif réussi."}

@app.get("/status")
def get_status():
    """Retourne l'état de connexion de l'Arduino."""
    return {"is_connected": ctrl.is_connected()}

@app.post("/reset")
def reset_arm():
    """Réinitialise les moteurs et la position XYZ du bras à (0, 0, 0)."""
    ctrl.reset()
    return {"message": "Réinitialisation effectuée."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
