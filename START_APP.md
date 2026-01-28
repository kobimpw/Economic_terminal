
# 🚀 Jak uruchomić Advanced Macro Trading Terminal (FastAPI)

## Szybki Start

### 1️⃣ Otwórz PowerShell w tym folderze
- Kliknij prawym przyciskiem myszy w Eksploratorze plików
- Wybierz "Otwórz w terminalu" lub "Open PowerShell window here"

### 2️⃣ Uruchom serwer
```powershell
python app.py
```

### 3️⃣ Otwórz przeglądarkę
- Aplikacja automatycznie otworzy się na: **http://localhost:8000**
- API Health: **http://localhost:8000/api/health**
- API Docs: **http://localhost:8000/docs**

---

## 🛑 Jak zatrzymać aplikację
- Naciśnij `Ctrl + C` w terminalu
- Lub zamknij okno terminala

---

## ⚠️ Rozwiązywanie problemów

### Problem: "ModuleNotFoundError"
**Rozwiązanie:** Zainstaluj zależności:
```powershell
pip install -r requirements.txt
```

### Problem: "FRED API Key not found"
**Rozwiązanie:** Upewnij się, że plik `.env` zawiera:
```
FRED_API_KEY=twój_klucz_api
```

### Problem: Port 8000 jest zajęty
**Rozwiązanie:**
Edytuj `app.py` i zmień port w ostatniej linii `uvicorn.run(..., port=8000)`.

---

**Powodzenia! 🚀**
