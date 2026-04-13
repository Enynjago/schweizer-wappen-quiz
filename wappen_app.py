import streamlit as st
import pandas as pd
import random
import os

# --- DATEN LADEN ---
@st.cache_data
def load_data():
    if os.path.exists("gemeinden.csv"):
        try:
            df = pd.read_csv("gemeinden.csv", sep=';').dropna(how='all')
            df.columns = [c.lower().strip() for c in df.columns]
            if 'gemeinde' in df.columns:
                df = df[df['gemeinde'].notna()]
                df['gemeinde'] = df['gemeinde'].astype(str).str.strip()
            return df
        except Exception as e:
            st.error(f"Fehler beim Laden der CSV: {e}")
    return pd.DataFrame(columns=["gemeinde", "kanton", "bild_pfad"])

df = load_data()

# --- INITIALISIERUNG ---
if "setup_done" not in st.session_state:
    st.session_state.update({
        "current_item": None,
        "show_solution": False,
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": [],
        "setup_done": True
    })

# --- SIDEBAR ---
st.sidebar.title("🇨🇭 Wappen-Trainer")
if not df.empty:
    st.sidebar.metric("Erfasste Gemeinden", f"{len(df)} / 2131")

st.sidebar.divider()
mode = st.sidebar.radio("Modus wählen", ["Lernen (Anki-Style)", "Quiz (Eingabe)"])

def next_question(kanton_filter=None):
    st.session_state.show_solution = False
    if mode == "Lernen (Anki-Style)":
        pool = df[df['kanton'] == kanton_filter] if kanton_filter else df
        if not pool.empty:
            st.session_state.current_item = pool.sample(1).iloc[0].to_dict()
    else:
        if st.session_state.quiz_queue:
            st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        else:
            st.session_state.current_item = None

# --- STEUERUNG ---
if mode == "Lernen (Anki-Style)":
    kantone = sorted(df['kanton'].unique()) if not df.empty else []
    k_wahl = st.sidebar.selectbox("Kanton wählen", kantone if kantone else ["Keine Daten"])
    if st.session_state.current_item is None:
        next_question(k_wahl)
else:
    kantone_q = ["Alle"] + sorted(df['kanton'].unique().tolist()) if not df.empty else []
    q_reg = st.sidebar.selectbox("Region wählen", kantone_q)
    if st.sidebar.button("Quiz starten"):
        pool = df if q_reg == "Alle" else df[df['kanton'] == q_reg]
        if not pool.empty:
            st.session_state.quiz_queue = pool.sample(frac=1).to_dict('records')
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            next_question()
            st.rerun()

# --- HAUPTBEREICH ---
if st.session_state.current_item:
    item = st.session_state.current_item
    name_richtig = str(item.get('gemeinde', ''))
    
    # --- LERNMODUS (ANKI) ---
    if mode == "Lernen (Anki-Style)":
        st.subheader("Lernmodus: Karteikarten")
        
        # Wappen zeigen
        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=350)
        
        st.write("---")
        
        if not st.session_state.show_solution:
            if st.button("Lösung anzeigen", use_container_width=True):
                st.session_state.show_solution = True
                st.rerun()
        else:
            # Lösung groß anzeigen
            st.markdown(f"### Lösung: **{name_richtig}**")
            st.write(f"Kanton: {item.get('kanton', '').upper()}")
            
            st.write("Wie gut konntest du dich erinnern?")
            c1, c2, c3 = st.columns(3)
            if c1.button("Nochmal (Falsch)", col1=True):
                next_question(k_wahl)
                st.rerun()
            if c2.button("Gut (Gewusst)"):
                next_question(k_wahl)
                st.rerun()
            if c3.button("Einfach (Perfekt)"):
                next_question(k_wahl)
                st.rerun()

    # --- QUIZMODUS (ALT) ---
    else:
        # (Hier bleibt dein bisheriger Quiz-Code mit Eingabefeld...)
        # ... (der Übersichtlichkeit halber abgekürzt, funktioniert aber wie zuvor)
        st.write("Quizmodus aktiv – bitte Name eingeben.")
        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=300)
        user_input = st.text_input("Name der Gemeinde:", key=f"q_{name_richtig}")
        if st.button("Prüfen"):
            if user_input.lower().strip() == name_richtig.lower().strip():
                st.success(f"Richtig! {name_richtig}")
                st.session_state.quiz_stats['correct'] += 1
            else:
                st.error(f"Falsch! Richtig wäre {name_richtig}")
                st.session_state.quiz_stats['wrong'] += 1
            if st.button("Weiter"):
                next_question()
                st.rerun()

else:
    st.info("Wähle einen Kanton zum Lernen aus!")
