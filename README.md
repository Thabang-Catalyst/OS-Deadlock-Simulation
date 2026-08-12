OS Deadlock Simulation

An interactive web-based Operating Systems simulation tool built with Python (Flask) and NetworkX 
that demonstrates real-time process concurrency, resource allocation, deadlock detection using Wait-For Graphs, and automated process termination recovery.

Features
Real-Time Concurrency Simulation: Simulates dynamic user (process) generation, execution, resource acquisition, and release cycles using Python background threads.
Wait-For Graph & Deadlock Detection: Uses NetworkX to build a real-time directed graph of process dependencies, instantly flagging cyclic deadlocks.
Automated Deadlock Recovery: Identifies deadlocked process chains and automatically resolves them by safely terminating the offending processes to free up system resources.
Interactive Web Dashboard: Monitor active users in handler frames, waiting queues, system utilization metrics, and live event logs.
Full Simulation Control: Start, pause, resume, and stop the simulation dynamically through responsive UI controls.

Tech Stack
Backend: Python, Flask, NetworkX, Threading
Frontend: HTML5, CSS3, JavaScript
Communication: RESTful JSON APIs

System Resources Simulated
The simulation features processes competing for the following shared resources:
DB Connection
Media Service
Notification Service
Message Queue
Update Feeds
