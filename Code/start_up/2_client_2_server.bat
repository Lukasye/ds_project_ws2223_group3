echo off
cd ..
start cmd /k python Server.py
start cmd /k python Client.py
start cmd /k python Server.py --port 10010 --opt 0
start cmd /k python Client.py --port 5710