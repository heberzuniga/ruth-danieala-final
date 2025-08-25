# Misión Bonos — MVP (Streamlit + Google Sheets)

Proyecto base listo para desplegar en **Streamlit Community Cloud** con **Python 3.11**.

## Estructura
```
mision_bonos/
├─ app.py               # Router principal (Streamlit) — incluye safe guards
├─ config.py            # Config y constantes
├─ services/
│  ├─ sheets.py         # Conexión a Google Sheets (gspread) — opcional
│  └─ storage_models.py # Validaciones / mapeos
├─ domain/
│  ├─ pricing.py        # DCF y bid/ask (mínimo viable)
│  ├─ events.py         # Composición de YTM con eventos
│  ├─ orders.py         # Validación de órdenes (stubs)
│  ├─ ledger.py         # Cupón / call (stubs)
│  └─ leaderboard.py    # Cálculo de ranking (mínimo viable)
├─ ui/
│  ├─ moderator.py      # Panel del Moderador
│  ├─ participant.py    # Panel del Participante
│  └─ components.py     # Helpers de UI (sort_safe, toasts, tablas)
├─ assets/
│  └─ sample_escenario.csv
└─ requirements.txt
```

## Despliegue en Streamlit Cloud
1. Sube este contenido a un repositorio (GitHub).
2. En el deploy, **Advanced settings → Python 3.11**.
3. Si quieres usar **Google Sheets**:
   - Carga en *Secrets*:
     - `gcp_service_account` (JSON completo de la Service Account)
     - `SPREADSHEET_KEY` (o pega una URL)  
4. Alternativa rápida (**demo local/CSV**): en el *sidebar* marca **Modo demo (CSV)** y carga `assets/sample_escenario.csv`.

## Comandos locales (opcional)
```bash
conda create -n bonos-py311 python=3.11 -y
conda activate bonos-py311
pip install -r requirements.txt
streamlit run app.py
```

## Notas
- Este MVP no requiere Sheets para correr en modo demo.
- Cuando configures Sheets, el Moderador podrá cargar escenario y la app leerá/escribirá en pestañas estándar.
