# Macro Trading Terminal - Podręcznik Budowy Aplikacji

Ten dokument przeprowadzi Cię krok po kroku przez proces budowania zaawansowanego terminala makroekonomicznego od zera.

## 1. Wymagania Wstępne
- Python 3.8+
- Klucze API: FRED (St. Louis Fed), Perplexity AI (opcjonalnie), NewsAPI (opcjonalnie)
- Biblioteki Python: `fastapi`, `uvicorn`, `pandas`, `numpy`, `statsmodels`, `scikit-learn`, `yfinance`, `fredapi`, `beautifulsoup4`

## 2. Struktura Projektu
Aplikacja wykorzystuje architekturę backendu (FastAPI) serwującego frontend (HTML/JS) z logiką analityczną w Pythonie.

```text
/
├── app.py                 # Główna aplikacja FastAPI (serwer)
├── config.py              # Konfiguracja i stałe
├── requirements.txt       # Zależności Python
├── src/
│   ├── core/
│   │   └── predictor.py   # Mózg aplikacji - zarządza modelami i danymi
│   ├── models/            # Implementacje modeli matematycznych
│   │   ├── arima_model.py
│   │   ├── monte_carlo.py
│   │   └── moving_average.py
│   ├── analysis/          # Narzędzia analityczne
│   │   └── market_correlation.py
│   └── integrations/      # Integracje z zewnętrznymi API (News, Stocks)
└── static/
    ├── app.js             # Logika frontendu (wykresy, interakcje)
    └── styles.css         # Wygląd
└── templates/
    └── index.html         # Główny widok
```

## 3. Kolejność Implementacji (Krok po Kroku)

### Krok 1: Konfiguracja Środowiska
Stwórz wirtualne środowisko i plik `requirements.txt`. Zainstaluj zależności.

### Krok 2: Podstawy Modeli (src/models/)
Zacznij od logiki matematycznej. Te pliki są niezależne od reszty.
1.  **`arima_model.py`**: Klasa używająca `statsmodels` do predykcji szeregów czasowych. Musi obsługiwać `auto_arima` lub ręczne dobieranie parametrów (p,d,q).
2.  **`monte_carlo.py`**: Symulacje losowe przyszłych ścieżek cen/wartości oparte na historycznej zmienności (Drift/Volatility).
3.  **`moving_average.py`**: Prosty model średnich kroczących jako punkt odniesienia (Baseline).

### Krok 3: Rdzeń Logiki (src/core/predictor.py)
To najważniejszy plik ("Orkiestrator"). Łączy on:
- **Pobieranie danych**: Używa biblioteki `fredapi` lub bezpośrednich zapytań HTTP do FRED.
- **Wywoływanie modeli**: Importuje klasy z Kroku 2 i uruchamia je na pobranych danych.
- **Ewaluacja**: Porównuje wyniki modeli (MAPE/RMSE) i wybiera najlepszy.
- **Integracje**: Obsługuje zapytania do AI (Perplexity) i NewsAPI.

*Dlaczego teraz?* Bo potrzebujesz działającego "mózgu" (backend logic) zanim zbudujesz interfejs. Możesz testować ten plik z poziomu konsoli/Jupyter Notebook.

### Krok 4: Serwer Backend (app.py)
Stwórz API, które udostępni logikę przez HTTP.
- Skonfiguruj `FastAPI`.
- Dodaj endpointy: 
    - `/api/calendar`: Zwraca listę wskaźników pogrupowaną datami.
    - `/api/analyze`: Przyjmuje POST z ID wskaźnika, wywołuje `PredictorCore` i zwraca JSON z prognozą.
    - `/api/precomputed/{series_id}`: Zwraca wcześniej obliczony wynik (cache).
- Zaimplementuj funkcję `precompute_all_models()` uruchamianą przy starcie aplikacji (`on_startup`), aby liczyć prognozy w tle i nie blokować użytkownika.

### Krok 5: Frontend - Widok (templates/index.html & static/styles.css)
Stwórz szkielet HTML i style CSS.
- **Układ**: Header, Market Glance (pasek ETF na górze), Główny Kalendarz (lista rozwijalnych kafelków).
- Użyj `Chart.js` do wizualizacji.

### Krok 6: Frontend - Logika (static/app.js)
To "mięśnie" aplikacji po stronie przeglądarki.
- **`loadCalendar()`**: Pobiera JSON z `/api/calendar` i dynamicznie generuje HTML (znaczniki `<details>` i `<summary>` dla kafelków).
- **`initializeTileContent()`**: Funkcja wywoływana przy rozwinięciu kafelka. Powinna leniwie (lazy-load) ładować wykresy, żeby strona startowa była szybka.
- **`renderTileForecastChart()`**: Rysuje wykresy historyczne + prognozy używając Chart.js.
- **`runTileAnalysis()`**: Obsługa przycisku "Run Analysis" - wysyła zapytanie do API i aktualizuje wykres w konkretnym kafelku.

### Krok 7: Zaawansowane Funkcje
Na końcu dodaj "bajer":
- **Integracja z AI**: Endpointy do Perplexity API generujące analizy tekstowe.
- **Scraping danych giełdowych**: Skrypty pobierające earningi spółek S&P 500 (np. z TradingView lub Yahoo Finance) i zapisujące je do bazy SQLite.
- **Daily AI Summary**: Agregacja wydarzeń dnia i generowanie jednego spójnego raportu.

## 4. Kluczowe Elementy Architektury

### Precompute (app.py)
Kluczowe dla UX. Użytkownik nie chce czekać 10 sekund na wynik modelu po kliknięciu.
System powinien "wiedzieć" wynik wcześniej.
```python
def precompute_all_models():
    # Uruchamia się w osobnym wątku (threading.Thread)
    # Iteruje po wszystkich wskaźnikach
    # Oblicza najlepszy model dla każdego
    # Zapisuje wynik w pamięci (słownik globalny)
```

### Date-Based Filtering (app.js)
Przy wykresach, przyciski "1Y", "2Y" muszą działać na podstawie daty (`Date` object), a nie liczby punktów (indeksów tablicy).
Dla danych dziennych 250 punktów to rok. Dla miesięcznych - 12 punktów.
Algorytm musi znaleźć indeks w tablicy dat, który odpowiada dacie sprzed X miesięcy.

### Skalowalny Frontend
Zamiast jednego globalnego wykresu (jak w prostych dashboardach), każdy kafelek to niezależny "mikro-dashboard" z własnym Canvasem (`<canvas class="forecast-chart">`).
Funkcje renderujące muszą przyjmować kontener (DOM Element) jako argument, aby wiedzieć gdzie rysować.

## 5. Uruchomienie
```bash
# 1. Zainstaluj zależności
pip install -r requirements.txt

# 2. Uruchom serwer
python app.py
```
Aplikacja wstanie na `http://localhost:8000`.
