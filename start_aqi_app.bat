@echo off
title AQI App Starter

echo Starting Flask Server...
cd /d D:\PYTHONCODE\AQI PREDICTION PROJECT
start cmd /k "python app.py"

timeout /t 5

echo Starting Flutter App...
cd /d C:\Flutter_projects\aqi_app
start cmd /k "flutter run"

echo All services are starting... Please wait!
exit
