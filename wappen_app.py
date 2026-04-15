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
        "q_color": "info", # success, error oder info
        "quiz_active": False,
        "quiz_finished": False,
        "last_pool": [],
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": [],
        "setup_done": True
    })

# --- SIDEBAR ---
st.sidebar.title("🇨🇭 Wappen-Trainer")
if not df.empty:
    st.sidebar.metric("Erfasste Gemeinden", f"{len(df)} / 2121")

mode = st.sidebar.radio("Modus wählen", ["Lernen (Anki)", "Quiz (Strenge Prüfung)"])

def next_question():
    st.session_state.q_answered = False
    st.session_state.q_feedback = None
    if st.session_state.quiz_queue:
        st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        st.session_state.quiz_finished = False
    else:
        st.session_state.current_item = None
        st.session_state.quiz_finished = True

# --- STEUERUNG ---
if mode == "Quiz (Strenge Prüfung)":
    kantone_q = ["Alle"] + sorted(df['kanton'].unique().tolist()) if not df.empty else []
    q_reg = st.sidebar.selectbox("Region wählen", kantone_q)
    if st.sidebar.button("Quiz starten"):
        pool = df if q_reg == "Alle" else df[df['kanton'] == q_reg]
        if not pool.empty:
            st.session_state.last_pool = pool.to_dict('records')
            st.session_state.quiz_queue = pool.sample(frac=1).to_dict('records')
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.quiz_active = True
            st.session_state.quiz_finished = False
            next_question()
            st.rerun()

# --- HAUPTBEREICH QUIZ ---
if mode == "Quiz (Strenge Prüfung)" and st.session_state.quiz_active:
    if not st.session_state.quiz_finished and st.session_state.current_item:
        item = st.session_state.current_item
        name_richtig = str(item.get('gemeinde', ''))
        s = st.session_state.quiz_stats
        
        st.subheader(f"Frage {s['correct'] + s['wrong'] + 1} von {s['total']}")
        
        # Wappen
        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=300)

        # Feedback-Anzeige
        if st.session_state.q_feedback:
            if st.session_state.q_color == "success": st.success(st.session_state.q_feedback)
            else: st.error(st.session_state.q_feedback)
            st.info("💡 Drücke einfach nochmals ENTER für das nächste Wappen.")

        # DAS FORMULAR
        with st.form("quiz_form", clear_on_submit=True):
            user_in = st.text_input("Name der Gemeinde:", key="main_input")
            submitted = st.form_submit_button("Prüfen / Weiter")
            
            if submitted:
                # Fall 1: User hat schon geantwortet und drückt nochmal Enter (Feld ist leer durch clear_on_submit)
                if st.session_state.q_answered:
                    next_question()
                    st.rerun()
                
                # Fall 2: User gibt eine Antwort ab
                elif user_in.strip() != "":
                    if user_in.lower().strip() == name_richtig.lower().strip():
                        st.session_state.q_feedback = f"Korrekt! Es ist {name_richtig}."
                        st.session_state.q_color = "success"
                        st.session_state.quiz_stats['correct'] += 1
                    else:
                        st.session_state.q_feedback = f"Falsch! Richtig wäre: {name_richtig}"
                        st.session_state.q_color = "error"
                        st.session_state.quiz_stats['wrong'] += 1
                        st.session_state.quiz_stats['wrong_list'].append(item)
                    st.session_state.q_answered = True
                    st.rerun()
                
                # Fall 3: User drückt Enter bei leerem Feld, ohne vorher geantwortet zu haben
                else:
                    st.warning("Bitte gib zuerst einen Namen ein!")

    elif st.session_state.quiz_finished:
        st.balloons()
        st.header("Quiz abgeschlossen!")
        s = st.session_state.quiz_stats
        st.write(f"Richtig: {s['correct']} | Falsch: {s['wrong']}")
        
        c1, c2 = st.columns(2)
        if c1.button("🔄 Alles nochmals"):
            st.session_state.quiz_queue = random.sample(st.session_state.last_pool, len(st.session_state.last_pool))
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            next_question()
            st.rerun()
        if s['wrong_list'] and c2.button(f"🎯 Nur Fehler ({len(s['wrong_list'])})"):
            st.session_state.quiz_queue = random.sample(s['wrong_list'], len(s['wrong_list']))
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            next_question()
            st.rerun()
else:
    st.info("Wähle links den Modus und starte das Training!")
