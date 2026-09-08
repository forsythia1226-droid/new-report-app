@echo off
title [Taihan] Daily Issue Report - DEMO
cd /d "%~dp0"

set "PYEXE=python"
%PYEXE% --version >nul 2>&1
if errorlevel 1 set "PYEXE=py"
%PYEXE% --version >nul 2>&1
if errorlevel 1 goto NOPYTHON

REM 첫 실행 시 이메일 입력 프롬프트에서 멈추는 것을 방지
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set STREAMLIT_SERVER_HEADLESS=true
set DEMO_MODE=true

echo ============================================================
echo   [대한전선] 일일현안 보고 - 데모 모드
echo ============================================================
echo.
echo [1/3] 파이썬 확인
%PYEXE% --version
echo.

echo [2/3] 필수 패키지 확인
%PYEXE% -c "import streamlit, gspread, dotenv" >nul 2>&1
if errorlevel 1 goto INSTALL
echo       설치 완료됨
goto READY

:INSTALL
echo       누락된 패키지를 설치합니다. 잠시 기다려 주세요...
%PYEXE% -m pip install -r requirements.txt
if errorlevel 1 goto PIPFAIL

:READY
echo.
if /i "%~1"=="check" goto CHECK

echo [3/3] 앱을 실행합니다.
echo       주소: http://localhost:8501
echo       잠시 후 브라우저가 자동으로 열립니다.
echo       종료하려면 이 창에서 Ctrl+C 를 누르거나 창을 닫으세요.
echo.

REM 서버가 뜰 시간을 준 뒤 브라우저를 연다 (약 6초 대기)
start "" /b cmd /c "ping -n 7 127.0.0.1 >nul & start "" http://localhost:8501"

%PYEXE% -m streamlit run issue_app.py --server.port 8501 --server.address 127.0.0.1
echo.
echo ============================================================
echo  앱이 종료되었습니다. 위에 오류 메시지가 있으면 알려주세요.
echo ============================================================
pause
exit /b 0

:CHECK
echo [3/3] 환경 점검
%PYEXE% -c "import config, org_store, issue_store, report_generator; print('   modules OK'); print('   divisions:', len(org_store.load_organization()))"
echo.
echo 점검이 끝났습니다.
pause
exit /b 0

:PIPFAIL
echo.
echo [오류] 패키지 설치에 실패했습니다. 위 메시지를 확인해 주세요.
pause
exit /b 1

:NOPYTHON
echo.
echo [오류] 파이썬을 찾을 수 없습니다.
echo        https://www.python.org 에서 설치한 뒤 다시 실행해 주세요.
pause
exit /b 1
