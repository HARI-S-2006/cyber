@echo off
REM Cyber Threat Visualizer - Start All Services (Batch wrapper)
REM Calls the PowerShell start script

powershell -ExecutionPolicy Bypass -File "%~dp0\start-all.ps1"