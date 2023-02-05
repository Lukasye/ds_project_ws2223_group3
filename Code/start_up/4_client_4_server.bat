echo off
cd ..
start cmd /k python Server.py --opt 0
start cmd /k python Server.py --port 10005 --opt 0
start cmd /k python Server.py --port 10010 --opt 0
start cmd /k python Server.py --port 10015 --opt 0
start cmd /k python Client.py
start cmd /k python Client.py --port 5710
start cmd /k python Client.py --port 5720
start cmd /k python Client.py --port 5730