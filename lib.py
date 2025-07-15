import math
import serial
import time
from enum import Enum
import os
from ikpy.chain import Chain

class MotorName(Enum):
    """
    Enumeration of the available motor names in the robotic arm.
    """
    SH1 = "SH1"  # Shoulder joint 1
    SH2 = "SH2"  # Shoulder joint 2
    SH3 = "SH3"  # Shoulder joint 3
    EL1 = "EL1"  # Elbow joint

# Placeholder conversion functions – adapt to your motor specifications
def angle_to_pos(angle: float) -> float:
    """
    Converts an angle in degrees to a raw motor position.
    """
    return angle * 10

def pos_to_angle(pos: float) -> float:
    """
    Converts a raw motor position to an angle in degrees.
    """
    return pos / 10

class ArduinoInterface:
    """
    Serial interface to communicate with the Arduino controller for multi-motor control.
    Supports sending movement commands, calibration, closed-loop control, and error reporting.
    """

    def __init__(self, port="COM5", baudrate=115200):
        """
        Initialize the serial connection with the Arduino.

        :param port: Serial port name (e.g., "COM5" on Windows or "/dev/ttyUSB0" on Linux)
        :param baudrate: Communication speed (default: 115200)
        """
        try:
            self.serial = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to connect to Arduino on {port}: {e}")

    def send_command(self, command: str):
        """
        Sends a raw command string to the Arduino over serial.

        :param command: The command string to send
        """
        try:
            self.serial.write((command + "\n").encode())
        except serial.SerialException as e:
            print(f"Serial communication error: {e}")

    def calibrate(self, motor_angles: dict[MotorName, float]):
        """
        Calibrates the given motors, ignoring read-only motors like EL1.

        :param motor_angles: Dictionary {motor_name: placeholder_angle}
        """
        ids = [motor.value for motor in motor_angles if motor != MotorName.EL1]
        if ids:
            command = "CALIBRATE_SYNC " + " ".join(ids)
            self.send_command(command)
            print(command)
        else:
            print("No motors available for calibration (EL1 is ignored).")

    def set_angle(self, motor_angles: dict[MotorName, float]):
        """
        Sets the target angle (in degrees) for each motor.

        :param motor_angles: Dictionary {motor_name: angle_in_degrees}
        """
        parts = [
            f"{motor.value} {angle:.2f}"
            for motor, angle in motor_angles.items()
            if motor != MotorName.EL1
        ]
        if parts:
            command = "SET_SYNC " + " ".join(parts)
            self.send_command(command)
            print(command)
        else:
            print("No valid angles specified.")

    def set_closed_loop(self, motor_angles: dict[MotorName, float]):
        """
        Enables closed-loop control for the specified motors.

        :param motor_angles: Dictionary {motor_name: placeholder_value}
        """
        ids = [motor.value[2] for motor in motor_angles if motor != MotorName.EL1]
        for id_ in ids:
            self.send_command(f"SET_CLOSED_LOOP {id_}")
            print(f"SET_CLOSED_LOOP {id_}")

    def set_idle(self, motor_angles: dict[MotorName, float]):
        """
        Deactivates the specified motors by setting them to IDLE mode.

        :param motor_angles: Dictionary {motor_name: placeholder_value}
        """
        ids = [motor.value[2] for motor in motor_angles if motor != MotorName.EL1]
        for id_ in ids:
            self.send_command(f"SET_IDLE {id_}")
            print(f"SET_IDLE {id_}")

    def get_latest_position(self, motor_angles: dict[MotorName, float]) -> dict[MotorName, float]:
        """
        Retrieves the latest known position for each specified motor.

        :param motor_angles: Dictionary {motor_name: placeholder_value}
        :return: Dictionary {motor_name: angle_in_degrees}
        """
        positions = {}
        for motor in motor_angles:
            self.send_command(f"GET {motor.value}")
            print(f"GET {motor.value}")
            response = self.serial.readline().decode(errors="ignore").strip()
            response = ''.join(c for c in response if c.isprintable())
            print(f"Raw response for {motor.name}: {repr(response)}")

            if response.startswith(f"{motor.value}:"):
                try:
                    pos = float(response.split(":")[1])
                    positions[motor] = pos  # Replace with pos_to_angle(pos) if conversion is needed
                except ValueError:
                    print(f"Failed to parse position for {motor.name}: {response}")
                    positions[motor] = None
            else:
                print(f"Unexpected response for {motor.name}: {repr(response)}")
                positions[motor] = None
        return positions

    def get_errors(self):
        """
        Fetches the list of current motor errors, if any.

        :return: List of integer error codes, or None on failure
        """
        self.send_command("GET_ERRORS")
        response = self.serial.readline().decode(errors="ignore").strip()
        if response.startswith("ERRORS:"):
            try:
                return [int(error) for error in response.split(":")[1].split(",")]
            except ValueError:
                print(f"Failed to parse error response: {response}")
        else:
            print(f"Unexpected response: {repr(response)}")
        return None

class Controller:
    """
    High-level controller for managing the robotic arm using inverse kinematics and Arduino communication.
    """

    def __init__(self, port="COM4", urdf_path=""):
        """
        Initializes the controller with Arduino interface and kinematic chain.

        :param port: Serial port to connect to Arduino
        :param urdf_path: Path to the URDF file describing the robot structure
        """
        self.arduino = ArduinoInterface(port)
        self.chain = Chain.from_urdf_file(urdf_path)
        for i, link in enumerate(self.chain.links):
            print(f"Link {i}: {link.name}, Bounds: {link.bounds}")
            if link.name in ["Base link", "joint_5"]:
                self.chain.active_links_mask[i] = False
        self.pos = {"x": 1.2, "y": 0.3, "z": -1.0}
        self.angles: dict[MotorName, float] = {
            MotorName.SH1: 0.0,
            MotorName.SH2: 0.0,
            MotorName.SH3: 0.0,
            MotorName.EL1: 0.0
        }

    def get_angle(self, motor: MotorName) -> float:
        """Returns the current angle for the specified motor."""
        if motor not in self.angles:
            raise ValueError(f"Invalid motor name: {motor}.")
        return self.angles[motor]

    def get_angles(self) -> dict[MotorName, float]:
        """Returns all current motor angles."""
        return self.angles.copy()

    def get_pos(self) -> dict[str, float]:
        """Returns the current XYZ position of the arm's end-effector."""
        return self.pos.copy()

    def goto(self, x: float, y: float, z: float, move: bool = True) -> dict[MotorName, float]:
        """
        Computes and applies the required joint angles to reach a given (x, y, z) position.

        :param x: Target X position
        :param y: Target Y position
        :param z: Target Z position
        :param move: If True, motors will be commanded to move
        :return: Dictionary of computed joint angles
        """
        if None in (x, y, z):
            raise ValueError("x, y, and z must all be provided.")

        target = [x, y, z]
        self.pos = {"x": x, "y": y, "z": z}
        res = self.chain.inverse_kinematics(target)

        joint_names = [joint.name for joint in self.chain.links[1:-1]]
        joint_angles = {
            MotorName[name]: float(angle) * 180 / math.pi
            for name, angle in zip(joint_names, res[1:-1])
        }

        if move:
            self.set_motors_angles(joint_angles)
            self.angles[MotorName.EL1] = target[2]

        return joint_angles

    def set_motor_angle(self, motor: MotorName, angle: float):
        """Sets a specific motor (excluding EL1) to a given angle in degrees."""
        if motor == MotorName.EL1:
            raise ValueError("EL1 is controlled by absolute Z position, not angle.")
        self.set_motors_angles({motor: angle})

    def set_motors_angles(self, motor_angles: dict[MotorName, float]):
        """Sets multiple motors to the given angles."""
        self.arduino.set_angle(motor_angles)
        self.angles.update(motor_angles)

    def reset(self):
        """Resets all joint angles and the end-effector position."""
        self.arduino.send_command("RESET")
        self.angles = {motor: 0.0 for motor in self.angles}
        self.pos = {"x": 0.0, "y": 0.0, "z": 0.0}

    def calibrate_all(self):
        """Calibrates all motors except EL1."""
        motors = {
            motor: 0.0 for motor in self.angles
            if motor != MotorName.EL1
        }
        self.arduino.calibrate(motors)

    def calibrate(self, motor: MotorName):
        """Calibrates a single motor, excluding EL1."""
        if motor == MotorName.EL1:
            raise ValueError("EL1 does not support calibration.")
        self.arduino.calibrate({motor: 0.0})

    def get_errors(self):
        """Retrieves error codes from the Arduino."""
        return self.arduino.get_errors()

    def update_from_arduino(self):
        """
        Synchronizes internal motor angles with the latest values received from the Arduino.
        """
        updated = self.arduino.get_latest_position(self.angles)
        for motor, angle in updated.items():
            if angle is not None:
                self.angles[motor] = angle
