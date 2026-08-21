@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul && goto run_py
where python >nul 2>nul && goto run_python

echo [ContextLens] Python was not found.
echo Please install Python 3.10 or newer from https://www.python.org/downloads/
pause
exit /b 1

:run_py
py -3 start.py
goto check_result

:run_python
python start.py

:check_result
if errorlevel 1 (
  echo.
  echo ContextLens stopped with an error. Please send this window to the project author.
  pause
)
