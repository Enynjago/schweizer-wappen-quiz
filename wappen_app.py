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
if "quiz_stats" not in st.session_state:
    st.session_state.update({
        "current_item": None,
        "q_answered": False,
        "q_feedback": None,
        "quiz_active": False,
        "quiz_finished": False,
        "quiz_queue": [],
        "last_pool": [],
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []}
    })

def next_question():
    if st.session_state.quiz_queue:
        st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        st.session_state.q_answered = False
        st.session_state.q_feedback = None
    else:
        st.session_state.quiz_finished = True

# --- SIDEBAR ---
st.sidebar.title("🇨🇭 Wappen-Trainer")
mode = st.sidebar.radio("Modus", ["Quiz", "Lernen"])

if mode == "Quiz":
    kantone = ["Alle"] + sorted(df['kanton'].unique().tolist()) if not df.empty else []
    wahl = st.sidebar.selectbox("Region", kantone)
    if st.sidebar.button("Quiz starten"):
        pool = df if wahl == "Alle" else df[df['kanton'] == wahl]
        if not pool.empty:
            st.session_state.last_pool = pool.to_dict('records')
            st.session_state.quiz_queue = pool.sample(frac=1).to_dict('records')
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.quiz_active = True
            st.session_state.quiz_finished = False
            next_question()
            st.rerun()

# --- QUIZ MODUS ---
if mode == "Quiz" and st.session_state.quiz_active:
    if not st.session_state.quiz_finished and st.session_state.current_item:
        item = st.session_state.current_item
        name_richtig = str(item.get('gemeinde', ''))
        s = st.session_state.quiz_stats
        
        st.subheader(f"Frage {s['correct'] + s['wrong'] + 1} von {s['total']}")
        
        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=300)

        # Feedback Anzeige (vor dem Formular, damit es nicht springt)
        if st.session_state.q_feedback:
            if "Korrekt" in st.session_state.q_feedback: st.success(st.session_state.q_feedback)
            else: st.error(st.session_state.q_feedback)

        # Das "Universal-Formular"
        # clear_on_submit sorgt dafür, dass das Feld nach Enter leer wird
        with st.form(key="action_form", clear_on_submit=True):
            user_in = st.text_input("Name eingeben & Enter:", key="input_text")
            
            # Ein einziger Button, der die Aktion steuert
            if not st.session_state.q_answered:
                button_label = "Prüfen"
            else:
                button_label = "WEITER (Enter drücken)"
                
            submitted = st.form_submit_button(button_label, use_container_width=True)

            if submitted:
                if not st.session_state.q_answered:
                    # Logik: Prüfen
                    if user_in.lower().strip() == name_richtig.lower().strip():
                        st.session_state.q_feedback = f"Richtig! Es ist {name_richtig}."
                        st.session_state.quiz_stats['correct'] += 1
                    else:
                        st.session_state.q_feedback = f"Falsch! Es ist {name_richtig}."
                        st.session_state.quiz_stats['wrong'] += 1
                        st.session_state.quiz_stats['wrong_list'].append(item)
                    st.session_state.q_answered = True
                    st.rerun()
                else:
                    # Logik: Weiter
                    next_question()
                    st.rerun()

    elif st.session_state.quiz_finished:
        st.balloons()
        st.header("Ergebnis")
        s = st.session_state.quiz_stats
        st.write(f"Du hast {s['correct']} von {s['total']} Wappen erkannt.")
        
        if st.button("Neues Quiz"):
            st.session_state.quiz_active = False
            st.rerun()
            
        if s['wrong_list'] and st.button("Nur Fehler wiederholen"):
            st.session_state.quiz_queue = random.sample(s['wrong_list'], len(s['wrong_list']))
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.quiz_finished = False
            next_question()
            st.rerun()

else:
    st.info("Klicke links auf 'Quiz starten'.")
