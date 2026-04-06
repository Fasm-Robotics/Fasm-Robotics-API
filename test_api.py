# tests/test_api.py
import os
import types
import pytest
from fastapi.testclient import TestClient

# IMPORTANT:
# - Remplace "main" par le nom réel de ton fichier (sans .py) qui contient app/ctrl/is_connected
#   ex: si ton fichier s'appelle "api.py" => import api as m
import main as m


# -------------------------
# Fakes / Mocks minimaux
# -------------------------
class FakeMotorEnum:
    def __init__(self, name): self.name = name

class FakeMotorName:
    __members__ = {"SH1": None, "SH2": None, "SH3": None, "EL1": None}
    def __getitem__(self, k): return FakeMotorEnum(k)

class FakeArduino:
    def __init__(self):
        self.last_closed_loop = []
        self.last_idle = []
        self.last_calibrate = []
        self.latest_positions = {}

    def get_latest_position(self, motors_dict):
        # retourne angle si connu sinon None
        out = {}
        for motor_enum in motors_dict.keys():
            out[motor_enum] = self.latest_positions.get(motor_enum.name, None)
        return out

    def set_closed_loop(self, motors_dict):
        self.last_closed_loop.append(list(motors_dict.keys()))

    def set_idle(self, motors_dict):
        self.last_idle.append(list(motors_dict.keys()))

    def calibrate(self, motors_dict):
        self.last_calibrate.append(list(motors_dict.keys()))

class FakeController:
    def __init__(self, port, urdf_path):
        self.port = port
        self.urdf_path = urdf_path
        self.arduino = FakeArduino()
        self._connected = True
        self.last_set_motor = None
        self.last_set_motors = None
        self.last_calibrate = None
        self.reset_called = False
        self.goto_calls = []

    def is_connected(self):
        return self._connected

    def goto(self, x, y, z, do_move: bool):
        self.goto_calls.append((x, y, z, do_move))
        # simule retour dict {MotorEnum: angle_deg}
        return {
            FakeMotorEnum("SH1"): 10.0,
            FakeMotorEnum("SH2"): 20.0,
            FakeMotorEnum("SH3"): 30.0,
            FakeMotorEnum("EL1"): 40.0,
        }

    def set_motor_angle(self, motor_enum, angle):
        self.last_set_motor = (motor_enum.name, angle)

    def set_motors_angles(self, angles_dict):
        # angles_dict: {MotorEnum: angle}
        self.last_set_motors = {k.name: v for k, v in angles_dict.items()}

    def calibrate(self, motor_enum):
        self.last_calibrate = motor_enum.name

    def reset(self):
        self.reset_called = True


# -------------------------
# Fixtures
# -------------------------
@pytest.fixture(autouse=True)
def patch_globals(monkeypatch):
    """
    - Patch MotorName/Controller dans ton module
    - Réinitialise ctrl/is_connected entre tests
    """
    monkeypatch.setattr(m, "MotorName", FakeMotorName())
    monkeypatch.setattr(m, "Controller", FakeController)
    m.ctrl = None
    m.is_connected = False
    yield
    m.ctrl = None
    m.is_connected = False

@pytest.fixture
def client():
    return TestClient(m.app)


# -------------------------
# Helpers
# -------------------------
def connect(client, port="COM4"):
    r = client.post("/connect", json={"port": port, "baudrate": 115200})
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    assert m.is_connected is True
    assert m.ctrl is not None


# -------------------------
# Tests: connexion / état
# -------------------------
def test_connect_ok(client):
    connect(client)
    assert isinstance(m.ctrl, FakeController)
    assert m.ctrl.port == "COM4"

def test_connect_idempotent(client):
    connect(client)
    r = client.post("/connect", json={"port": "COM7", "baudrate": 115200})
    assert r.status_code == 200
    assert r.json()["message"] == "Déjà connecté."
    # doit rester l'ancien ctrl
    assert m.ctrl.port == "COM4"

def test_disconnect_ok(client):
    connect(client)
    r = client.post("/disconnect")
    assert r.status_code == 200
    assert m.is_connected is False
    assert m.ctrl is None

def test_disconnect_idempotent(client):
    r = client.post("/disconnect")
    assert r.status_code == 200
    assert r.json()["message"] == "Déjà déconnecté."

def test_status_uses_ctrl_is_connected_when_connected(client):
    connect(client)
    r = client.get("/status")
    assert r.status_code == 200
    assert r.json() == {"is_connected": True}

def test_status_when_not_connected_current_code_breaks(client):
    # Ton code fait: return {"is_connected": ctrl.is_connected()}
    # alors que ctrl = None => AttributeError => 500
    r = client.get("/status")
    assert r.status_code == 500


# -------------------------
# Tests: cinématique inverse
# -------------------------
@pytest.mark.parametrize("path,do_move", [
    ("/reverseK", True),
    ("/preview-reverseK", False),
])
def test_inverse_kinematics_requires_connection(client, path, do_move):
    r = client.post(path, json={"x": 1, "y": 2, "z": 3})
    assert r.status_code == 400
    assert r.json()["detail"] == "Arduino non connecté."

def test_inverse_kinematics_ok(client):
    connect(client)
    r = client.post("/reverseK", json={"x": 1, "y": 2, "z": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["SH1"] == 10.0
    assert body["EL1"] == 40.0
    assert m.ctrl.goto_calls[-1] == (1, 2, 3, True)

def test_preview_inverse_kinematics_ok(client):
    connect(client)
    r = client.post("/preview-reverseK", json={"x": 1, "y": 2, "z": 3})
    assert r.status_code == 200
    assert m.ctrl.goto_calls[-1] == (1, 2, 3, False)


# -------------------------
# Tests: angles / moteurs / limites (validation)
# -------------------------
def test_set_motor_angle_requires_connection(client):
    r = client.post("/set-motor-angle", json={"motor": "SH1", "angle": 10})
    assert r.status_code == 400

def test_set_motor_angle_invalid_motor(client):
    connect(client)
    r = client.post("/set-motor-angle", json={"motor": "BAD", "angle": 10})
    assert r.status_code == 500
    assert "Nom de moteur invalide" in r.json()["detail"]

def test_set_motor_angle_ok(client):
    connect(client)
    r = client.post("/set-motor-angle", json={"motor": "SH1", "angle": 12.5})
    assert r.status_code == 200
    assert m.ctrl.last_set_motor == ("SH1", 12.5)

def test_set_sync_angles_invalid_motor(client):
    connect(client)
    r = client.post("/set-sync-angles", json={"angles": {"SH1": 1.0, "BAD": 2.0}})
    assert r.status_code == 500
    assert "Moteur invalide" in r.json()["detail"]

def test_set_sync_angles_ok(client):
    connect(client)
    r = client.post("/set-sync-angles", json={"angles": {"SH1": 1.0, "SH2": 2.0}})
    assert r.status_code == 200
    assert m.ctrl.last_set_motors == {"SH1": 1.0, "SH2": 2.0}

def test_get_motor_angle_invalid_motor(client):
    connect(client)
    r = client.get("/get-motor-angle?motor=BAD")
    assert r.status_code == 500
    assert "Nom de moteur invalide" in r.json()["detail"]

def test_get_motor_angle_read_none_is_error(client):
    connect(client)
    # pas de position stockée => None => erreur
    r = client.get("/get-motor-angle?motor=SH1")
    assert r.status_code == 500
    assert "Erreur de lecture" in r.json()["detail"]

def test_get_motor_angle_ok(client):
    connect(client)
    m.ctrl.arduino.latest_positions["SH1"] = 33.0
    r = client.get("/get-motor-angle?motor=SH1")
    assert r.status_code == 200
    assert r.json()["angle_degrees"] == 33.0


# -------------------------
# Tests: calibrations / états
# -------------------------
def test_calibrate_invalid_motor(client):
    connect(client)
    r = client.post("/calibrate", json={"motor": "BAD"})
    assert r.status_code == 500

def test_calibrate_ok(client):
    connect(client)
    r = client.post("/calibrate", json={"motor": "EL1"})
    assert r.status_code == 200
    assert m.ctrl.last_calibrate == "EL1"

def test_calibrate_sync_filters_invalid_names(client):
    connect(client)
    r = client.post("/calibrate-sync", json={"motors": ["SH1", "BAD", "SH2"]})
    assert r.status_code == 200
    # FakeArduino.calibrate reçoit seulement les moteurs valides
    called = m.ctrl.arduino.last_calibrate[-1]
    names = [x.name for x in called]
    assert names == ["SH1", "SH2"]

def test_set_closed_loop_invalid_motor(client):
    connect(client)
    r = client.post("/set-closed-loop", json={"motors": ["BAD"]})
    assert r.status_code == 500

def test_set_closed_loop_ok(client):
    connect(client)
    r = client.post("/set-closed-loop", json={"motors": ["SH1", "SH2"]})
    assert r.status_code == 200
    # appelé une fois par moteur dans ton code
    assert len(m.ctrl.arduino.last_closed_loop) == 2

def test_set_idle_ok(client):
    connect(client)
    r = client.post("/set-idle", json={"motors": ["SH1", "SH2"]})
    assert r.status_code == 200
    assert len(m.ctrl.arduino.last_idle) == 2


# -------------------------
# Tests: reset / reboot
# -------------------------
def test_reboot_ok(client):
    r = client.post("/reboot")
    assert r.status_code == 200
    assert r.json()["status"] == "success"

def test_reset_calls_ctrl_reset(client):
    connect(client)
    r = client.post("/reset")
    assert r.status_code == 200
    assert m.ctrl.reset_called is True
