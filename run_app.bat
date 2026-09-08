@echo off
title [Taihan] Daily Issue Report
cd /d "%~dp0"

set "PYEXE=python"
%PYEXE% --version >nul 2>&1
if errorlevel 1 set "PYEXE=py"
%PYEXE% --version >nul 2>&1
if errorlevel 1 goto NOPYTHON

REM 첫 실행 시 이메일 입력 프롬프트에서 멈추는 것을 방지
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_HEADLESS=true
set DEMO_MODE=false

echo ============================================================
echo   [대한전선] 일일현안 보고 - 운영 모드
echo ============================================================
echo.

if not exist ".env" echo [경고] .env 파일이 없습니다. .env.example 을 복사해 값을 채워 주세요.
if not exist "service_account.json" echo [경고] service_account.json 이 없습니다. 서비스 계정 키를 이 폴더에 넣어 주세요.
echo.

%PYEXE% -c "import streamlit, gspread, dotenv" >nul 2>&1
if errorlevel 1 %PYEXE% -m pip install -r requirements.txt

echo 앱을 실행합니다 - 주소: http://localhost:8501
echo 종료하려면 이 창에서 Ctrl+C 를 누르세요.
echo.

start "" /b cmd /c "ping -n 7 127.0.0.1 >nul & start "" http://localhost:8501"

%PYEXE% -m streamlit run issue_app.py --server.port 8501 --server.address 127.0.0.1
echo.
echo ============================================================
echo  앱이 종료되었습니다. 위에 오류 메시지가 있으면 알려주세요.
echo ============================================================
pause
exit /b 0

:NOPYTHON
echo.
echo [오류] 파이썬을 찾을 수 없습니다.
pause
exit /b 1
