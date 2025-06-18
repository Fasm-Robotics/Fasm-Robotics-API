import math
import serial
import time
from enum import Enum
import os
from ikpy.chain import Chain

class MotorName(Enum):
    SH1 = "SH1"
    SH2 = "SH2"
    SH3 = "SH3"
    EL1 = "EL1"  # AMT102V (lecture seule)

# Fonctions de conversion placeholder (à adapter selon ton système)
def angle_to_pos(angle: float) -> float:
    return angle * 10  # Exemple de conversion angle → position moteur

def pos_to_angle(pos: float) -> float:
    return pos / 10  # Exemple de conversion position moteur → angle

class ArduinoInterface:
    """
    Interface de communication série avec un Arduino pour contrôler plusieurs moteurs simultanément.
    Permet l'envoi de commandes groupées ou individuelles pour calibrer, positionner, activer ou désactiver des moteurs.
    """

    def __init__(self, port="COM5", baudrate=115200):
        """
        Initialise la connexion série avec l'Arduino.
        :param port: Port série utilisé (ex: "COM5")
        :param baudrate: Vitesse de communication (par défaut: 115200)
        """
        try:
            self.serial = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)  # Attente pour laisser le temps à l'Arduino de démarrer
        except serial.SerialException as e:
            raise ConnectionError(f"Impossible d'établir la connexion avec l'Arduino sur {port}: {e}")

    def send_command(self, command: str):
        """
        Envoie une commande brute à l'Arduino.
        :param command: Chaîne de commande à envoyer
        """
        try:
            self.serial.write((command + "\n").encode())
        except serial.SerialException as e:
            print(f"Erreur de communication série : {e}")

    def calibrate(self, motor_angles: dict[MotorName, float]):
        """
        Calibre les moteurs spécifiés (hors EL1).
        :param motor_angles: Dictionnaire {nom_moteur: angle}, angles ignorés ici
        """
        ids = [motor.value for motor in motor_angles if motor != MotorName.EL1]
        if ids:
            commande = "CALIBRATE_SYNC " + " ".join(ids)
            self.send_command(commande)
            print(commande)
        else:
            print("Aucun moteur valide à calibrer (EL1 est ignoré).")

    def set_angle(self, motor_angles: dict[MotorName, float]):
        """
        Définit les angles cibles des moteurs spécifiés.
        :param motor_angles: Dictionnaire {nom_moteur: angle_en_degrés}
        """
        parts = []
        for motor, angle in motor_angles.items():
            if motor != MotorName.EL1:
                parts.append(f"{motor.value} {(angle):.2f}")
        if parts:
            commande = "SET_SYNC " + " ".join(parts)
            self.send_command(commande)
            print(commande)
        else:
            print("Aucun angle défini pour des moteurs valides.")

    def set_closed_loop(self, motor_angles: dict[MotorName, float]):
        """
        Active le mode de contrôle en boucle fermée pour les moteurs (hors EL1).
        :param motor_angles: Dictionnaire {nom_moteur: angle}, angles ignorés ici
        """
        ids = [motor.value[2] for motor in motor_angles if motor != MotorName.EL1]
        if not ids:
            print("Aucun moteur compatible avec le mode boucle fermée.")
            return
        for id_ in ids:
            self.send_command(f"SET_CLOSED_LOOP {id_}")
            print(f"SET_CLOSED_LOOP {id_}")

    def set_idle(self, motor_angles: dict[MotorName, float]):
        """
        Désactive les moteurs (hors EL1) en les mettant à l'état IDLE.
        :param motor_angles: Dictionnaire {nom_moteur: angle}, angles ignorés ici
        """
        ids = [motor.value[2] for motor in motor_angles if motor != MotorName.EL1]
        if not ids:
            print("Aucun moteur à désactiver (EL1 ignoré).")
            return
        for id_ in ids:
            self.send_command(f"SET_IDLE {id_}")
            print(f"SET_IDLE {id_}")

    def get_latest_position(self, motor_angles: dict[MotorName, float]) -> dict[MotorName, float]:
        """
        Récupère la dernière position connue pour chaque moteur fourni,
        convertie en angle (en degrés).
        
        :param motor_angles: Dictionnaire {nom_moteur: valeur_placeholder}
                            (valeurs ignorées ici, seul le nom est utilisé)
        :return: Dictionnaire {nom_moteur: angle_en_degrés}, ou None pour les moteurs en erreur
        """
        positions = {}
        for motor in motor_angles:
            self.send_command(f"GET {motor.value}")
            print(f"GET {motor.value}")
            response = self.serial.readline().decode(errors="ignore").strip()
            response = ''.join(c for c in response if c.isprintable())

            print(f"Réponse brute pour {motor.name} : {repr(response)}")
            if response.startswith(f"{motor.value}:"):
                try:
                    pos = float(response.split(":")[1])
                    angle = (pos)
                    positions[motor] = angle
                except ValueError:
                    print(f"Erreur de parsing de la position pour {motor.name} : {response}")
                    positions[motor] = None
            else:
                print(f"Réponse inattendue pour {motor.name} : {repr(response)}")
                positions[motor] = None
        return positions


    def get_errors(self):
        """
        Récupère la liste des erreurs actuelles des moteurs, si disponibles.
        :return: Liste d'entiers représentant les erreurs, ou None en cas de problème
        """
        self.send_command("GET_ERRORS")
        response = self.serial.readline().decode(errors="ignore").strip()
        if response.startswith("ERRORS:"):
            try:
                return [int(error) for error in response.split(":")[1].split(",")]
            except ValueError:
                print(f"Erreur lors du parsing de la réponse : {response}")
        else:
            print(f"Réponse inattendue : {repr(response)}")
        return None

class Controller:
    """
    Contrôleur principal du bras robotisé.
    Gère les angles des moteurs, la position XYZ cible, et communique avec l'Arduino.
    """

    def __init__(self, port="COM5", urdf_path=""):
        # self.arduino = ArduinoInterface(port)
        self.chain = Chain.from_urdf_file(urdf_path)
        self.pos = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.angles: dict[MotorName, float] = {
            MotorName.SH1: 0.0,
            MotorName.SH2: 0.0,
            MotorName.SH3: 0.0,
            MotorName.EL1: 0.0
        }

    def get_angle(self, motor: MotorName) -> float:
        """
        Récupère l'angle actuel d'un moteur donné.
        """
        if motor not in self.angles:
            raise ValueError(f"Nom de moteur invalide : {motor}.")
        return self.angles[motor]

    def get_angles(self) -> dict[MotorName, float]:
        """
        Récupère l'ensemble des angles des moteurs.
        """
        return self.angles.copy()

    def get_pos(self) -> dict[str, float]:
        """
        Retourne la dernière position cible atteinte (XYZ).
        """
        return self.pos.copy()

    def goto(self, x: float, y: float, z: float, move: bool = True) -> dict[MotorName, float]:
        """
        Calcule les angles nécessaires pour atteindre la position (x, y, z)
        et commande les moteurs en conséquence.
        """
        if None in (x, y, z):
            raise ValueError("Tous les paramètres x, y et z doivent être fournis.")

        target = [x, y, z]
        self.pos = {"x": x, "y": y, "z": z}

        res = self.chain.inverse_kinematics(target)
        joint_names = [joint.name for joint in self.chain.links[1:-1]]
        joint_angles = {
            MotorName[name]: float(angle) * 180 / math.pi
            for name, angle in zip(joint_names, res[1:-1])
        }
        if move:
            # Mise à jour des moteurs articulés
            self.set_motors_angles(joint_angles)
            # Mise à jour de EL1 séparément si utile (position absolue sur Z)
            self.angles[MotorName.EL1] = target[2]

        return joint_angles

    def set_motor_angle(self, motor: MotorName, angle: float):
        """
        Définit un angle en degrés pour un seul moteur (hors EL1).
        """
        if motor == MotorName.EL1:
            raise ValueError("EL1 est contrôlé en position absolue (pas en angle relatif).")

        self.set_motors_angles({motor: angle})

    def set_motors_angles(self, motor_angles: dict[MotorName, float]):
        """
        Définit les angles (en degrés) de plusieurs moteurs simultanément.
        """
        self.arduino.set_angle(motor_angles)
        self.angles.update(motor_angles)

    def reset(self):
        """
        Réinitialise les angles et la position du robot.
        """
        self.arduino.send_command("RESET")
        self.angles = {motor: 0.0 for motor in self.angles}
        self.pos = {"x": 0.0, "y": 0.0, "z": 0.0}

    def calibrate_all(self):
        """
        Calibre automatiquement tous les moteurs sauf EL1.
        """
        moteurs = {
            motor: 0.0 for motor in self.angles
            if motor != MotorName.EL1
        }
        self.arduino.calibrate(moteurs)

    def calibrate(self, motor: MotorName):
        """
        Calibre un seul moteur.
        """
        if motor == MotorName.EL1:
            raise ValueError("EL1 ne supporte pas la calibration.")
        self.arduino.calibrate({motor: 0.0})

    def get_errors(self):
        """
        Récupère les erreurs de communication ou de statut moteur.
        """
        return self.arduino.get_errors()

    def update_from_arduino(self):
        """
        Met à jour les angles internes depuis les valeurs réelles mesurées par les moteurs.
        """
        updated = self.arduino.get_latest_position(self.angles)
        for motor, angle in updated.items():
            if angle is not None:
                self.angles[motor] = angle
