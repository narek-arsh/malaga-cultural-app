# Málaga Cultural (MVP)

## Estructura
- `config/feeds.yaml` — instituciones (on/off), URLs de listados.
- `scrapers/` — colector y scrapers por institución (con `__init__.py`).
- `data/` — `catalog.jsonl` (salida normalizada), `manual_events.csv`, `curated.json`.
- `app/streamlit_app.py` — app Streamlit con filtros por fecha/categoría.

## Uso local
```
pip install -r requirements.txt
python scrapers/collector.py
streamlit run app/streamlit_app.py
```

## Salida
- `data/sources/{id}.json` — items por institución.
- `data/catalog.jsonl` — todos los eventos.

## Manual
- Añade eventos en `data/manual_events.csv` (ver columnas).

