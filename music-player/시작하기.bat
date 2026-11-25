@echo off
chcp 65001 >nul
rem 윈도우용 시작 파일. 더블클릭해서 실행하세요.
rem Node.js 버전 확인, 처음이면 필요한 파일 설치, 브라우저 열기, 서버 실행
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 goto nonode

node server\node-check.js
if errorlevel 1 goto fail

if exist node_modules goto run
echo 처음 실행이라 필요한 파일을 설치합니다. 잠시 기다려 주세요...
call npm install --no-audit --no-fund
if errorlevel 1 goto installfail

:run
if "%PORT%"=="" set PORT=3000
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:%PORT%"
node server\main.js
goto fail

:nonode
echo Node.js가 설치되어 있지 않습니다.
echo https://nodejs.org 에서 LTS 버전 22 이상을 설치한 뒤 다시 실행하세요.
goto fail

:installfail
echo 설치에 실패했습니다. 위 메시지를 확인하세요.

:fail
echo.
pause
