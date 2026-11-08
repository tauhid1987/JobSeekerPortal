@echo off
cd /d "%~dp0"
echo Pushing JobMatch to GitHub. If a sign-in window opens, complete it.
echo.
git push origin main
echo.
echo If you see "main -> main" above, it worked. Otherwise copy the text above and send it.
pause
