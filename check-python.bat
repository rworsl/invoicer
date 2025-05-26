@echo off
echo Python Information:
python --version
python -c "import sys; print^('Python path:', sys.executable^)"
python -c "import sys; print^('Python version:', sys.version^)"
echo.
echo Testing basic imports:
python -c "print^('Testing imports...'^); import os, sys, json; print^('✅ Basic imports work'^)"
echo.
echo Flask test:
python -c "import flask; print^('✅ Flask works, version:', flask.__version__^)"
echo.
pause
