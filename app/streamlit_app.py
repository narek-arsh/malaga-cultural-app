
import streamlit as st
import pandas as pd
import json, os
from datetime import date, datetime

st.set_page_config(page_title="Málaga Cultural", layout="wide")

st.title("Agenda cultural · Málaga")

# Load data
records = []
if os.path.exists("data/catalog.jsonl"):
    with open("data/catalog.jsonl","r",encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
df = pd.DataFrame(records)

# Manual CSV
if os.path.exists("data/manual_events.csv"):
    try:
        m = pd.read_csv("data/manual_events.csv")
        # normalize minimal fields
        if not m.empty:
            m["source_id"] = m.get("source_id","manual")
            dfm = pd.DataFrame([{
                "id": f"manual-{i}",
                "source_id": row.get("source_id","manual"),
                "source_url": row.get("source_url",""),
                "categoria": row.get("categoria","actividad"),
                "titulo": row.get("titulo","(sin título)"),
                "descripcion": row.get("descripcion",""),
                "fecha_inicio": row.get("fecha_inicio"),
                "fecha_fin": row.get("fecha_fin") or row.get("fecha_inicio"),
                "ocurrencias": str(row.get("ocurrencias","")).split(";") if pd.notna(row.get("ocurrencias")) else [],
                "all_day": True,
                "lugar": row.get("lugar",""),
                "imagen_url": row.get("imagen_url",""),
                "timezone": "Europe/Madrid",
            } for i,row in m.iterrows()])
            df = pd.concat([df, dfm], ignore_index=True)
    except Exception as e:
        st.warning(f"No se pudo cargar manual_events.csv: {e}")

if df.empty:
    st.info("No hay datos todavía. Ejecuta el colector.")
    st.stop()

# Date filters
today = date.today()
col1, col2, col3 = st.columns(3)
with col1:
    preset = st.selectbox("Rango rápido", ["Hoy","Mañana","Próximos 7 días","Este mes","Todo"], index=2)
with col2:
    start = st.date_input("Desde", today)
with col3:
    end = st.date_input("Hasta", today)

if preset == "Hoy":
    start = end = today
elif preset == "Mañana":
    start = end = today.fromordinal(today.toordinal()+1)
elif preset == "Próximos 7 días":
    end = date.fromordinal(today.toordinal()+7)
elif preset == "Este mes":
    start = date(today.year, today.month, 1)
    if today.month==12:
        end = date(today.year, 12, 31)
    else:
        from calendar import monthrange
        end = date(today.year, today.month, monthrange(today.year, today.month)[1])
# else: use chosen

cats = sorted(df["categoria"].dropna().unique().tolist())
sel_cats = st.multiselect("Categorías", cats, default=cats)

def overlaps(row):
    try:
        fi = datetime.fromisoformat(str(row.get("fecha_inicio"))).date()
        ff = datetime.fromisoformat(str(row.get("fecha_fin"))).date()
    except Exception:
        return False
    return not (ff < start or fi > end)

filtered = df[df["categoria"].isin(sel_cats)]
filtered = filtered[filtered.apply(overlaps, axis=1)]

st.caption(f"{len(filtered)} eventos")

# Render cards
for _, r in filtered.sort_values("fecha_inicio").iterrows():
    with st.container(border=True):
        cols = st.columns([1,2])
        with cols[0]:
            if r.get("imagen_url"):
                st.image(r.get("imagen_url"))
        with cols[1]:
            st.markdown(f"### {r.get('titulo','(sin título)')}")
            fi = r.get("fecha_inicio"); ff = r.get("fecha_fin")
            if fi and ff:
                st.write(f"**{fi} – {ff}**")
            elif fi:
                st.write(f"**{fi}**")
            if r.get("lugar"):
                st.caption(r.get("lugar"))
            if r.get("descripcion"):
                st.write(r.get("descripcion"))
            if r.get("source_url"):
                st.link_button("Ver en origen", r.get("source_url"))
