
# Robot Arm API – Control of an Arduino-Based Robotic Arm

This repository contains a Python-based system to control a robotic arm driven by an Arduino board. It consists of:

1. A **core Python library** (`lib.py`) for serial communication, inverse kinematics, motor control, and calibration.
2. A **FastAPI-based REST API** (`api.py`) to expose the functionalities through HTTP routes.
3. Additional assets such as STL meshes, URDF files, and a Postman collection for easy testing.

All joint angles are expressed in **degrees**. The system uses serial communication to interact with the Arduino.

---

## Website

Learn more about the project on our official website:  
**[https://fasmrobotics.tech](https://fasmrobotics.tech)**

---

## Features

- Connect to the robotic arm via serial port (e.g., COM4)
- Control individual motor angles
- Set all motor angles simultaneously
- Execute inverse kinematics from XYZ coordinates
- Calibrate motors (individually or all at once)
- Toggle closed-loop or idle mode

---

## Project Structure

```
robot-arm-api/
├── Api.py                # FastAPI entry point for HTTP routes
├── lib.py                # Core logic for motor control and kinematics
├── postman.json          # API documentation for Postman
├── robotarm_corrected.urdf # Arm 3d model used for simulation
├── meshes/               # STL files for physical parts
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker image for deployment
├── README.md             # This file
```

---

## Getting Started

### Prerequisites

- Python 3.9
- An Arduino board with compatible firmware (listening via serial)
- The Robotic Arm connected to the Arduino Board

### Installation

Clone the repository and install the dependencies

---

## Running the API

```bash
python3.9 api.py
```

The API will be accessible at:  
**http://localhost:8000**

You can access the interactive Swagger documentation at:  
**http://localhost:8000/docs**

---

## License

This project is provided for educational and prototyping purposes.

---

## Contact

For questions, improvements, or contributions, please contact the team through the [official site](https://fasmrobotics.tech).
