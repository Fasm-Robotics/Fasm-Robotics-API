import serial
import time


class ArduinoController:
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        """
        Initialise la connexion série avec l'Arduino.
        :param port: Port série (ex. "COM3" sur Windows ou "/dev/ttyUSB0" sur Linux/Mac).
        :param baudrate: Vitesse de transmission en bauds.
        :param timeout: Temps d'attente pour la lecture série.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None

    def connect(self):
        """
        Établit une connexion série avec l'Arduino.
        """
        try:
            self.serial_connection = serial.Serial(
                port=self.port, baudrate=self.baudrate, timeout=self.timeout
            )
            time.sleep(2)  # Temps pour permettre à l'Arduino de se réinitialiser
            print(f"Connexion établie avec {self.port} à {self.baudrate} bauds.")
        except serial.SerialException as e:
            raise Exception(f"Erreur lors de la connexion : {e}")

    def disconnect(self):
        """
        Ferme la connexion série.
        """
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("Connexion série fermée.")

    def send_message(self, message: str):
        """
        Envoie un message à l'Arduino.
        :param message: Le message à envoyer.
        """
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.write(f"{message}\n".encode('utf-8'))
                print(f"Message envoyé : {message}")
            except serial.SerialException as e:
                raise Exception(f"Erreur lors de l'envoi du message : {e}")
        else:
            raise Exception("La connexion série n'est pas ouverte.")

    def read_message(self) -> str:
        """
        Lit un message provenant de l'Arduino.
        :return: Le message reçu.
        """
        if self.serial_connection and self.serial_connection.is_open:
            try:
                message = self.serial_connection.readline().decode('utf-8').strip()
                print(f"Message reçu : {message}")
                return message
            except serial.SerialException as e:
                raise Exception(f"Erreur lors de la lecture du message : {e}")
        else:
            raise Exception("La connexion série n'est pas ouverte.")

    def reset_motors(self):
        """
        Réinitialise les angles des moteurs.
        """
        self.send_message("reset")
        return self.read_message()

class MotorController(ArduinoController):
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        """
        Initialise le contrôleur du moteur.
        Hérite de ArduinoController.
        :param port: Port série (ex: "COM3").
        :param baudrate: Taux de transmission en bauds (par défaut 9600).
        :param timeout: Temps d'attente pour la communication série.
        """
        super().__init__(port, baudrate, timeout)
        # Angles des moteurs
        self.angle_motor1 = 0.0
        self.angle_motor2 = 0.0
        self.angle_motor3 = 0.0

    def update_motor1(self, angle: float) -> str:
        """
        Met à jour l'angle du moteur 1.
        :param angle: L'angle cible pour le moteur 1.
        :return: Réponse de l'Arduino.
        """
        self.angle_motor1 = angle
        self.send_message(f"motor1:{self.angle_motor1}")
        return self.read_message()

    def update_motor2(self, angle: float) -> str:
        """
        Met à jour l'angle du moteur 2.
        :param angle: L'angle cible pour le moteur 2.
        :return: Réponse de l'Arduino.
        """
        self.angle_motor2 = angle
        self.send_message(f"motor2:{self.angle_motor2}")
        return self.read_message()

    def update_motor3(self, angle: float) -> str:
        """
        Met à jour l'angle du moteur 3.
        :param angle: L'angle cible pour le moteur 3.
        :return: Réponse de l'Arduino.
        """
        self.angle_motor3 = angle
        self.send_message(f"motor3:{self.angle_motor3}")
        return self.read_message()

    def get_motor1(self) -> float:
        """
        Récupère l'angle actuel du moteur 1.
        :return: Angle actuel du moteur 1.
        """
        self.send_message("get_motor1")
        response = self.read_message()
        self.angle_motor1 = float(response) if response else 0.0
        return self.angle_motor1

    def get_motor2(self) -> float:
        """
        Récupère l'angle actuel du moteur 2.
        :return: Angle actuel du moteur 2.
        """
        self.send_message("get_motor2")
        response = self.read_message()
        self.angle_motor2 = float(response) if response else 0.0
        return self.angle_motor2

    def get_motor3(self) -> float:
        """
        Récupère l'angle actuel du moteur 3.
        :return: Angle actuel du moteur 3.
        """
        self.send_message("get_motor3")
        response = self.read_message()
        self.angle_motor3 = float(response) if response else 0.0
        return self.angle_motor3