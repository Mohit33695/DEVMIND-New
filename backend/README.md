# DevMind AI - Backend Foundation

Minimal FastAPI backend foundation for **DevMind AI** Software Engineering Intelligence Platform.

---

## 🛠️ Prerequisites

* **Python**: `3.10+` (Tested on Python `3.13.3`)
* **pip**: Included with Python

---

## 🚀 Setup & Execution Guide (Windows)

### 1. Open Terminal in `backend/`
```powershell
cd backend
```

### 2. Create Python Virtual Environment
Create an isolated virtual environment named `venv`:
```powershell
python -m venv venv
```

### 3. Activate Virtual Environment
* **PowerShell**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Command Prompt (cmd)**:
  ```cmd
  venv\Scripts\activate.bat
  ```

*(If PowerShell execution policy blocks script activation, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)*

### 4. Install Required Packages
```powershell
pip install -r requirements.txt
```

### 5. Start FastAPI Development Server
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🧪 Verification & Endpoints

Once running, access:
* **Health Check**: [`http://127.0.0.1:8000/api/health`](http://127.0.0.1:8000/api/health)
* **Interactive OpenAPI Docs**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)

---

## 🔒 CORS Configuration

CORS is configured in `app/main.py` specifically for local frontend development origins:
* `http://localhost:5173`
* `http://127.0.0.1:5173`
