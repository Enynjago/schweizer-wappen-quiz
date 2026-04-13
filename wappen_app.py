import streamlit as st
import pandas as pd
import random
import os
from thefuzz import fuzz

# --- DATEN LADEN ---
@st.cache_data
def load_data():
    if os.path.exists("gemeinden.csv"):
        df = pd.read_csv("gemeinden.csv", sep=';')
        df.columns = [c.lower().strip() for c in df.columns]
        return df
    return pd.DataFrame(columns=["gemeinde", "kanton", "bild_pfad"])

df = load_data()

# --- HILFSFUNKTION FÜR BUCHSTABEN-TIPPS ---
def get_hint(word, level):
    if level == 0: return ""
    parts = word.split('-')
    hint_parts = []
    for p in parts:
        if len(p) <= level:
            hint_parts.append(p)
        else:
            hint_parts.append(p[:level] + "." * (len(p)-level))
    return "Tipp: " + "-".join(hint_parts)

# --- INITIALISIERUNG SESSION STATE ---
if "current_item" not in st.session_state:
    st.session_state.current_item = None

if "setup_done" not in st.session_state:
    st.session_state.update({
        "attempts": 0,
        "answered": False,
        "feedback_msg": None,
        "feedback_type": None, # "success", "error", "warning"
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": [],
        "setup_done": True
    })

# --- SIDEBAR ---
st.sidebar.title("🇨🇭 Wappen-Trainer")
anzahl_erfasst = len(df)
st.sidebar.metric("Erfasste Gemeinden", f"{anzahl_erfasst} / 2131")
st.sidebar.progress(min(anzahl_erfasst / 2131, 1.0))

st.sidebar.divider()
mode = st.sidebar.radio("Modus wählen", ["Lernen", "Quiz"])

# --- LOGIK: NÄCHSTES WAPPEN ---
def next_question(kanton_filter=None):
    if mode == "Lernen":
        pool = df[df['kanton'] == kanton_filter] if kanton_filter else df
        if not pool.empty:
            st.session_state.current_item = pool.sample(1).iloc[0].to_dict()
    else: # Quiz
        if st.session_state.quiz_queue:
            st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        else:
            st.session_state.current_item = None
    
    st.session_state.attempts = 0
    st.session_state.answered = False
    st.session_state.feedback_msg = None

# --- STEUERUNG ---
if mode == "Lernen":
    kantone = sorted(df['kanton'].unique()) if not df.empty else []
    kanton_wahl = st.sidebar.selectbox("Kanton lernen", kantone if kantone else ["Keine Daten"])
    if st.sidebar.button("Nächstes Wappen / Start"):
        next_question(kanton_wahl)
        st.rerun()
else: # QUIZ
    kantone_quiz = ["Alle"] + sorted(df['kanton'].unique().tolist()) if not df.empty else ["Keine Daten"]
    quiz_region = st.sidebar.selectbox("Quiz-Region", kantone_quiz)
    if st.sidebar.button("Quiz starten"):
        pool = df if quiz_region == "Alle" else df[df['kanton'] == quiz_region]
        if not pool.empty:
            queue = pool.sample(frac=1).to_dict('records')
            st.session_state.quiz_queue = queue
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(queue), "wrong_list": []}
            next_question()
            st.rerun()

# --- HAUPTBEREICH ---
if st.session_state.current_item is not None:
    item = st.session_state.current_item
    
    if mode == "Quiz":
        s = st.session_state.quiz_stats
        beantwortet = s['correct'] + s['wrong']
        st.subheader(f"Frage {beantwortet + 1} von {s['total']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Richtig", s['correct'])
        c2.metric("Falsch", s['wrong'])
        quote = (s['correct'] / beantwortet * 100) if beantwortet > 0 else 0
        c3.metric("Quote", f"{quote:.1f}%")

    # Wappen anzeigen
    if os.path.exists(item['bild_pfad']):
        st.image(item['bild_pfad'], width=300)
    
    # Lern-Tipps (nur anzeigen wenn noch nicht gelöst)
    if mode == "Lernen" and not st.session_state.answered and st.session_state.attempts > 0:
        st.info(get_hint(item['gemeinde'], st.session_state.attempts))

    # Feedback-Anzeige (Wichtig für die Lösung)
    if st.session_state.feedback_msg:
        if st.session_state.feedback_type == "success":
            st.success(st.session_state.feedback_msg)
        elif st.session_state.feedback_type == "error":
            st.error(st.session_state.feedback_msg)
        elif st.session_state.feedback_type == "warning":
            st.warning(st.session_state.feedback_msg)

    # Eingabefeld
    user_input = st.text_input("Name der Gemeinde:", key=f"input_{item['gemeinde']}", disabled=st.session_state.answered)

    if not st.session_state.answered:
        if st.button("Prüfen"):
            score = fuzz.ratio(user_input.lower().strip(), item['gemeinde'].lower().strip())
            
            if score == 100:
                st.session_state.feedback_msg = f"Korrekt! Das ist {item['gemeinde']}."
                st.session_state.feedback_type = "success"
                if mode == "Quiz": st.session_state.quiz_stats['correct'] += 1
                st.session_state.answered = True
            else:
                if mode == "Lernen":
                    st.session_state.attempts += 1
                    if st.session_state.attempts >= 3:
                        st.session_state.feedback_msg = f"Nicht ganz. Die richtige Lösung ist: {item['gemeinde']}"
                        st.session_state.feedback_type = "error"
                        st.session_state.answered = True
                    else:
                        st.session_state.feedback_type = "warning"
                        st.session_state.feedback_msg = f"Falsch! Versuch {st.session_state.attempts}/3."
                else: # Quizmodus
                    st.session_state.feedback_msg = f"Falsch! Die richtige Lösung ist: {item['gemeinde']}"
                    st.session_state.feedback_type = "error"
                    st.session_state.quiz_stats['wrong'] += 1
                    st.session_state.quiz_stats['wrong_list'].append(item)
                    st.session_state.answered = True
            st.rerun()
    
    if st.session_state.answered:
        if st.button("Nächstes Wappen ➡️"):
            next_question(kanton_wahl if mode == "Lernen" else None)
            st.rerun()

elif mode == "Quiz" and st.session_state.quiz_stats['total'] > 0:
    st.balloons()
    st.header("Quiz beendet!")
    s = st.session_state.quiz_stats
    st.write(f"Ergebnis: {s['correct']} von {s['total']} richtig.")
    if s['wrong_list']:
        st.subheader("Wiederhole deine Fehler:")
        if st.button("Nur Fehler nochmals prüfen"):
            st.session_state.quiz_queue = s['wrong_list'].copy()
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(s['wrong_list']), "wrong_list": []}
            next_question()
            st.rerun()
else:
    st.info("Wähle links einen Modus und klicke auf Start!")
