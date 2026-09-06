@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python neni nainstalovan. & pause & exit /b 1)
python -m pip install -r requirements.txt
start "UCEBNICE SERVER" cmd /k "cd /d "%~dp0" && python app.py"
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5000/login
exit
