# 📊 Advanced Macro Trading Terminal

Zaawansowany terminal do analizy makroekonomicznej w stylu Bloomberg z integracją AI, wieloma modelami predykcyjnymi i analizą korelacji rynkowych.

![Terminal Screenshot](https://img.shields.io/badge/Status-Production-green)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green)

## 🌟 Funkcjonalności

### 📅 Kalendarz Ekonomiczny
- **Widok kalendarza** w stylu Bloomberg z datami publikacji wskaźników
- **Karty dni** z możliwością zwijania/rozwijania
- **Automatyczne grupowanie** wskaźników według dat publikacji
- **Scraping dat** z FRED API

### 🤖 Modele Predykcyjne
1. **ARIMA** - Autoregressive Integrated Moving Average
   - Konfigurowalne parametry (p, d, q)
   - Pełne statystyki (AIC, BIC, HQIC, p-values)
   - Analiza istotności parametrów

2. **Moving Average** - Średnia krocząca
   - Wielookresowa (możliwość dodania wielu okien)
   - Ensemble averaging
   - Optymalizacja dla stabilnych trendów

3. **Monte Carlo** - Symulacja stochastyczna
   - Konfigurowalna liczba symulacji
   - Percentile-based confidence intervals
   - Analiza zmienności

### 📈 Wizualizacje
1. **Wykres główny**: Historia + Prognoza z pasmami błędów (±1 RMSE, ±2 RMSE)
2. **Wykres testowy**: Porównanie rzeczywistych vs prognozowanych wartości
3. **Wykres różnicowania**: Analiza różnic z przełączaniem widoków
   - Rzeczywiste różnice
   - Prognozowane różnice
   - Błędy różnicowania

### 🔬 Analiza AI
- **Perplexity AI Research**: Głęboka analiza wskaźnika z cytatami i źródłami
- **News Sentiment**: Analiza sentymentu artykułów (0-100) z NLP
- **Model Quality Assessment**: Automatyczna ocena jakości modelu

### 📊 Korelacje Rynkowe
- **S&P 500** + 11 sektorowych ETF-ów
- **Korelacja długoterminowa** (3 lata danych)
- **Korelacja natychmiastowa** (same-day impact w dniu publikacji)
- **Beta** i interpretacja siły/kierunku

## 🚀 Instalacja

### 1. Przejdź do katalogu projektu
```bash
cd c:\Users\kobos\AI_Projects\Get-etf-data\FRED_DATA\MODEL_PREDYKCYJNY
```

### 2. Instalacja zależności
```bash
pip install -r requirements.txt
```

### 3. Konfiguracja API Keys
Edytuj plik `.env` i uzupełnij klucz FRED:

```bash
# .env
FRED_API_KEY=twoj_klucz_fred  # WYMAGANY!
```

#### Gdzie uzyskać klucze API:
- **FRED API**: https://fred.stlouisfed.org/docs/api/api_key.html (WYMAGANY)
- **Perplexity AI**: https://www.perplexity.ai/settings/api (opcjonalny - już uzupełniony)
- **News API**: https://newsapi.org/register (opcjonalny - już uzupełniony)

## 💻 Uruchomienie

### FastAPI Backend
```bash
python app.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:8000`
Api Documentation: `http://localhost:8000/docs`

## 📖 Instrukcja Użytkowania

### 1. Widok Kalendarza
- Po uruchomieniu zobaczysz kalendarz z datami publikacji wskaźników
- Kliknij na **kartę dnia** aby rozwinąć wskaźniki publikowane tego dnia
- Każda karta pokazuje liczbę wskaźników i ich nazwy

### 2. Analiza Wskaźnika
1. **Rozwiń kartę wskaźnika** klikając na jego nazwę
2. **Wybierz model** (ARIMA / Moving Average / Monte Carlo)
3. **Skonfiguruj parametry**:
   - **ARIMA**: p, d, q (order)
   - **Moving Average**: okna (np. "3,6,12")
   - **Monte Carlo**: liczba symulacji
4. **Ustaw parametry testowe**:
   - Test Period: ile miesięcy użyć do walidacji
   - Forecast Horizon: ile miesięcy prognozować
5. **Kliknij "Run Analysis"**

### 3. Interpretacja Wyników

#### Wykresy
- **Wykres 1**: Zielona linia = historia, Pomarańczowa = prognoza, Obszary = pasma błędów
- **Wykres 2**: Porównanie test period (jak dobrze model przewidział przeszłość)
- **Wykres 3**: Analiza różnicowania (przełączaj między actual/predicted/error)

#### Statystyki
- **AIC/BIC/HQIC**: Niższe = lepszy model
- **RMSE**: Root Mean Square Error (błąd średniokwadratowy)
- **MAPE**: Mean Absolute Percentage Error (błąd procentowy)
- **P-Values**: < 0.05 = parametr istotny statystycznie

#### AI Opinion
- Automatyczna ocena jakości modelu
- Rekomendacje dotyczące użycia
- Ostrzeżenia o potencjalnych problemach

#### Market Correlation
- **Long-Term Corr**: Jak wskaźnik koreluje z rynkiem długoterminowo
- **Immediate Corr**: Jak rynek reaguje w dniu publikacji
- **Beta**: Wrażliwość rynku na zmiany wskaźnika

## 🗂️ Struktura Projektu

```
MODEL_PREDYKCYJNY/
├── streamlit_app.py      # Główna aplikacja Streamlit
├── app.py                # FastAPI backend (alternatywny)
├── ARIMA.py              # Core prediction engine
├── config.py             # Konfiguracja (wskaźniki, parametry)
├── requirements.txt      # Zależności Python
├── .env                  # Klucze API (NIE commituj!)
├── .env.example          # Template dla .env
├── .gitignore            # Ignorowane pliki
└── README.md             # Ta dokumentacja
```

## 🔧 Konfiguracja

### Dodawanie Nowych Wskaźników

Edytuj `config.py`:

```python
SERIES_DICT = {
    "nazwa_wskaznika": "FRED_SERIES_ID",
    # ...
}

SERIES_NAMES = {
    "FRED_SERIES_ID": "Czytelna Nazwa",
    # ...
}
```

### Zmiana Parametrów Domyślnych

```python
DEFAULT_PARAMS = {
    "ARIMA": {
        "order": (1, 1, 1),  # (p, d, q)
        "n_test": 12,        # miesiące testowe
        "h_future": 6        # miesiące prognozy
    },
    # ...
}
```

## 📊 Wskaźniki Ekonomiczne

Obecnie obsługiwane wskaźniki:

| Kategoria | Wskaźnik | FRED ID |
|-----------|----------|---------|
| **Labor** | Unemployment Rate | UNRATE |
| **Labor** | Job Openings | JTSJOL |
| **Labor** | Continued Claims | CCSA |
| **Consumer** | Consumer Sentiment | UMCSENT |
| **Consumer** | Real Retail Sales | RRSFS |
| **Consumer** | Vehicle Sales | TOTALSA |
| **Housing** | New Home Sales | HSN1F |
| **Housing** | Building Permits | PERMIT |
| **Production** | Industrial Production | INDPRO |
| **Production** | Capacity Utilization | TCU |
| **Credit** | Consumer Credit | CCLACBW027SBOG |
| **Credit** | Bank Credit | WLCFLPCL |
| **Financial** | Financial Stress Index | STLFSI4 |
| **Rates** | Yield Curve Spread | T10Y2Y |

## 🐛 Troubleshooting

### "FRED API Key not found"
- Sprawdź czy plik `.env` istnieje
- Upewnij się że `FRED_API_KEY=` jest uzupełniony
- Restart aplikacji

### "Could not calculate correlations"
- Sprawdź połączenie internetowe
- Yahoo Finance może być tymczasowo niedostępny
- Spróbuj ponownie za chwilę

### "Perplexity API error"
- Sprawdź limit API calls (darmowy plan ma ograniczenia)
- Zweryfikuj poprawność klucza API

### Wolne ładowanie kalendarza
- Pierwsze ładowanie scrapuje daty z FRED (może trwać 1-2 min)
- Kolejne ładowania używają cache (1h TTL)
- Rozważ zwiększenie `CACHE_TTL` w `config.py`

## 🌐 Hosting

### Streamlit Cloud (Darmowy)
1. Push kod na GitHub
2. Połącz z https://streamlit.io/cloud
3. Dodaj secrets w dashboard (API keys)
4. Deploy!

### Heroku
```bash
# Dodaj Procfile:
web: streamlit run streamlit_app.py --server.port=$PORT
```

## 📝 Changelog

### v2.0 (2026-01-19)
- ✨ Kalendarz ekonomiczny w stylu Bloomberg
- 🤖 Integracja Perplexity AI
- 📰 News sentiment analysis
- 📈 Market correlation analysis
- 🎨 Bloomberg-style dark theme
- 📊 3 interaktywne wykresy Plotly

### v1.0 (2026-01-19)
- 🚀 Podstawowy model ARIMA
- 📊 Streamlit dashboard
- 📈 Wizualizacje prognozy

## 📄 Licencja

MIT License - użyj jak chcesz!

## 👨‍💻 Autor

Stworzony z ❤️ dla analizy makroekonomicznej

---

**⚠️ Disclaimer**: Ten terminal służy wyłącznie celom edukacyjnym i analitycznym. Nie stanowi porady inwestycyjnej. Zawsze przeprowadzaj własną analizę przed podejmowaniem decyzji inwestycyjnych.
