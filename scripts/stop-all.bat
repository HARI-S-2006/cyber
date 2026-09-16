@echo off
REM Cyber Threat Visualizer - Stop All Services (Batch wrapper)
REM Calls the PowerShell stop script

powershell -ExecutionPolicy Bypass -File "%~dp0\stop-all.ps1"