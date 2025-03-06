import odrive
from odrive.enums import (
    AXIS_STATE_FULL_CALIBRATION_SEQUENCE,
    AXIS_STATE_CLOSED_LOOP_CONTROL,
    AXIS_STATE_IDLE,
)
import asyncio
from enum import Enum

class MotorName(Enum):
    SH1 = "SH1"
    SH2 = "SH2"
    SH3 = "SH3"

class ODriveMotor:
    def __init__(self, axis):
        """
        Initialize an ODrive motor instance for a given axis.
        """
        self.axis = axis
        self.angle = 0.0
        self.size = 15

    def set_angle(self, angle):
        """Set the target angle for the motor."""
        if angle < -360 or angle > 360:
            raise ValueError("Angle must be between -360 and 360 degrees.")
        self.angle = float(angle)
        self.axis.controller.input_pos = angle * (self.size / 360)

    def set_velocity(self, velocity):
        """Set the target velocity for the motor."""
        self.axis.controller.input_vel = velocity

    def get_angle(self):
        """Get the current angle of the motor."""
        return self.angle

    def get_velocity(self):
        """Get the current velocity of the motor."""
        return self.axis.encoder.vel_estimate

    def calibrate(self):
        """Run the full calibration sequence for the motor."""
        self.axis.requested_state = AXIS_STATE_FULL_CALIBRATION_SEQUENCE
        while self.axis.current_state != AXIS_STATE_IDLE:
            pass

    def set_closed_loop_control(self):
        """Set the motor to closed-loop control mode."""
        self.axis.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL

    def set_idle(self):
        """Set the motor to idle mode."""
        self.axis.requested_state = AXIS_STATE_IDLE


class Controller:
    def __init__(self):
        """Initialize the controller with an empty dictionary to store motors."""
        self.motors = {}  # Dictionary to store motors by name
        self.pos = {"x": 0, "y": 0, "z": 0}
        self.ready = False

    async def add_motor(self, serial_number, name):
        """
        Asynchronously add a motor to the controller using its serial number.

        Args:
            serial_number (str): The serial number of the ODrive.
            name (MotorName): A unique name from the MotorName enum.
        """
        if not isinstance(name, MotorName):
            raise ValueError(f"Invalid motor name: {name}. Use MotorName Enum.")

        odrive_instance = await self._find_odrive_by_serial(serial_number)
        
        if odrive_instance:
            self.motors[name] = ODriveMotor(odrive_instance.axis0)
            print(f"Motor '{name.value}' added successfully.")
        else:
            print(f"Motor '{name.value}' could not be found.")

    async def _find_odrive_by_serial(self, serial_number):
        """Asynchronously find an ODrive by its serial number."""
        print(f"Searching for ODrive with serial number: {serial_number}...")
        while True:
            try:
                odrive_instance = odrive.find_any(serial_number=serial_number, timeout=5)
                if odrive_instance:
                    print(f"ODrive found: {odrive_instance.serial_number}")
                    return odrive_instance
            except Exception as e:
                print(f"Error while searching for ODrive: {e}")
            await asyncio.sleep(1)

    def get_motor(self, name):
        """Retrieve a motor by its name."""
        if not isinstance(name, MotorName):
            raise ValueError(f"Invalid motor name: {name}. Use MotorName Enum.")
        return self.motors.get(name)
    
    def update_pos(self, new_pos):
        """
        Move the motors to a specific position.
        """
        print(f"Moving motors to x={new_pos['x']}, y={new_pos['y']}, z={new_pos['z']}...")
        self.pos = new_pos
    
    def set_pos(self, x: int, y: int, z: int):
        """
        Set the position of the motors.
        """
        self.update_pos({"x": x, "y": y, "z": z})
        print(f"Position set to x={x}, y={y}, z={z}.")

    def get_pos(self):
        """
        Get the current position of the motors.
        """
        return self.pos

    def reboot(self, name=None):
        """Reboot a specific motor or all motors."""
        if name:
            if not isinstance(name, MotorName):
                raise ValueError(f"Invalid motor name: {name}. Use MotorName Enum.")
            motor = self.motors.get(name)
            if motor:
                motor.axis.odrive.reboot()
                print(f"Motor '{name.value}' rebooted.")
            else:
                print(f"Motor '{name.value}' not found.")
        else:
            for motor_name, motor in self.motors.items():
                motor.axis.odrive.reboot()
                print(f"Motor '{motor_name.value}' rebooted.")
            print("All motors rebooted.")

    def exit(self):
        """
        Set the motors to idle.
        """
        for motor in self.motors.values():
            motor.set_idle()
    
    def init(self):
        """
        Initialize all motors in closed-loop control mode.
        """
        for motor in self.motors.values():
            # check if error
            if motor.error != 0:
                motor.set_idle()
                motor.error = 0
                motor.set_closed_loop_control()
                while motor.current_state != AXIS_STATE_IDLE:
                    pass
        for motor in self.motors.values():
            motor.controller.config.control_mode = 3  # CTRL_MODE_POSITION_CONTROL
            motor.set_closed_loop_control()
        self.ready = True
        self.get_motor(MotorName.SH3).set_angle(105)
        self.get_motor(MotorName.SH1).set_angle(-22)
