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
        "q_answered": False,
        "q_feedback": None,
        "quiz_active": False,
        "quiz_finished": False,
        "last_pool": [],
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": [],
        "setup_done": True
    })

# --- HILFSFUNKTIONEN ---
def next_question():
    if st.session_state.quiz_queue:
        st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        st.session_state.q_answered = False
        st.session_state.q_feedback = None
        st.session_state.quiz_finished = False
    else:
        st.session_state.current_item = None
        st.session_state.quiz_finished = True

# --- SIDEBAR ---
st.sidebar.title("🇨🇭 Wappen-Trainer")
mode = st.sidebar.radio("Modus", ["Lernen", "Quiz"])

if mode == "Quiz":
    kantone_q = ["Alle"] + sorted(df['kanton'].unique().tolist()) if not df.empty else []
    q_reg = st.sidebar.selectbox("Region wählen", kantone_q)
    if st.sidebar.button("Quiz starten"):
        pool = df if q_reg == "Alle" else df[df['kanton'] == q_reg]
        if not pool.empty:
            st.session_state.last_pool = pool.to_dict('records')
            st.session_state.quiz_queue = pool.sample(frac=1).to_dict('records')
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.quiz_active = True
            next_question()
            st.rerun()

# --- HAUPTBEREICH QUIZ ---
if mode == "Quiz" and st.session_state.quiz_active:
    if not st.session_state.quiz_finished and st.session_state.current_item:
        item = st.session_state.current_item
        name_richtig = str(item.get('gemeinde', ''))
        s = st.session_state.quiz_stats
        
        st.subheader(f"Wappen {s['correct'] + s['wrong'] + 1} von {s['total']}")
        
        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=300)

        # Feedback-Bereich
        if st.session_state.q_feedback:
            if "Korrekt" in st.session_state.q_feedback:
                st.success(st.session_state.q_feedback)
            else:
                st.error(st.session_state.q_feedback)
            st.info("Drücke ENTER für das nächste Wappen")

        # DAS FORMULAR (Der Kern des Enter-Problems)
        with st.form(key="quiz_form", clear_on_submit=True):
            user_in = st.text_input("Name der Gemeinde:", key="input_field")
            submit = st.form_submit_button("Senden")
            
            if submit:
                # Logik: Wenn schon geantwortet wurde -> nächstes Wappen
                if st.session_state.q_answered:
                    next_question()
                    st.rerun()
                # Logik: Wenn noch nicht geantwortet wurde -> prüfen
                elif user_in.strip():
                    if user_in.lower().strip() == name_richtig.lower().strip():
                        st.session_state.q_feedback = f"Korrekt! Das ist {name_richtig}."
                        st.session_state.quiz_stats['correct'] += 1
                    else:
                        st.session_state.q_feedback = f"Falsch! Lösung: {name_richtig}"
                        st.session_state.quiz_stats['wrong'] += 1
                        st.session_state.quiz_stats['wrong_list'].append(item)
                    st.session_state.q_answered = True
                    st.rerun()

    elif st.session_state.quiz_finished:
        st.header("Quiz beendet!")
        s = st.session_state.quiz_stats
        st.write(f"Ergebnis: {s['correct']} von {s['total']} richtig.")
        if st.button("Nochmal"):
            st.session_state.quiz_active = False
            st.rerun()

else:
    st.write("Wähle links eine Region und klicke auf 'Quiz starten'.")
