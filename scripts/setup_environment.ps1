Write-Host "Setting up AlphaScope environment..."
python -m venv venv
.\venv\Scripts\python -m pip install --upgrade pip
.\venv\Scripts\python -m pip install -e .
Write-Host "Environment ready."
