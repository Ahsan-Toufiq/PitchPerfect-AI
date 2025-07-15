# Virtual Environment Setup

This project is now configured to run in a clean virtual environment, keeping your global Python environment clean.

## 🧹 Global Environment Cleanup

The following packages were removed from your global Python environment:
- `fastapi==0.104.1`
- `uvicorn==0.24.0`
- `pydantic==2.5.0`
- `pydantic-settings==2.1.0`
- `python-multipart==0.0.6`
- `sqlalchemy==2.0.23`
- `psycopg2-binary==2.9.9`
- `alembic==1.12.1`
- `playwright==1.40.0`
- `requests==2.31.0`
- `beautifulsoup4==4.12.2`
- `lxml==4.9.3`
- `aiosmtplib==3.0.1`
- `jinja2==3.1.2`
- `python-dotenv==1.0.0`
- `aiofiles==23.2.1`
- `greenlet==3.0.1`
- `Mako==1.3.10`
- `pyee==11.0.1`

## 🚀 Quick Start

### Option 1: Using the startup script (Recommended)
```bash
# For bash/zsh
./start.sh

# For fish shell
./start.fish
```

### Option 2: Manual setup
```bash
# 1. Activate virtual environment
source .venv/bin/activate.fish  # For fish shell
# OR
source .venv/bin/activate       # For bash/zsh

# 2. Install dependencies (if not already installed)
pip install -r requirements.txt

# 3. Install Playwright browsers (if not already installed)
playwright install

# 4. Start backend
python server.py

# 5. In another terminal, start frontend
cd frontend && npm run dev
```

## 📦 Virtual Environment Details

- **Location**: `.venv/` directory in project root
- **Python Version**: 3.11.5
- **Dependencies**: All project dependencies are isolated in the virtual environment
- **Activation**: Use `source .venv/bin/activate.fish` for fish shell

## 🌐 Access Points

Once running, you can access:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Troubleshooting

### If you get "ModuleNotFoundError"
```bash
# Activate virtual environment first
source .venv/bin/activate.fish

# Then install missing dependencies
pip install email-validator loguru tldextract
```

### If Playwright browsers are missing
```bash
# Activate virtual environment first
source .venv/bin/activate.fish

# Then install browsers
playwright install
```

### If you need to recreate the virtual environment
```bash
# Remove old environment
rm -rf .venv

# Create new environment
python -m venv .venv

# Activate and install dependencies
source .venv/bin/activate.fish
pip install -r requirements.txt
playwright install
```

## ✅ Benefits

1. **Clean Global Environment**: No project dependencies in your global Python installation
2. **Isolated Dependencies**: Each project has its own package versions
3. **Easy Reproduction**: Anyone can recreate the exact environment
4. **No Conflicts**: Different projects can use different package versions
5. **Easy Cleanup**: Just delete the `.venv` folder to remove everything

Your global Python environment is now clean and the project runs entirely within its virtual environment! 🎉 