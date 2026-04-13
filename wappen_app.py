import streamlit as st
import pandas as pd
import random
import os
from thefuzz import fuzz

# --- DATEN LADEN ---
@st.cache_data
def load_data():
    if os.path.exists("gemeinden.csv"):
        try:
            # Erzwungene Semikolon-Trennung für deine Datei
            df = pd.read_csv("gemeinden.csv", sep=';')
            df.columns = [c.lower().strip() for c in df.columns]
            return df
        except Exception as e:
            st.error(f"Fehler beim Laden: {e}")
    return pd.DataFrame(columns=["gemeinde", "kanton", "bild_pfad"])

df = load_data()

# --- HILFSFUNKTION FÜR TIPPS ---
def get_hint(word, level):
    if not word or level == 0: return ""
    parts = str(word).split('-')
    hint_parts = []
    for p in parts:
        if len(p) <= level:
            hint_parts.append(p)
        else:
            hint_parts.append(p[:level] + "." * (len(p)-level))
    return "Tipp: " + "-".join(hint_parts)

# --- INITIALISIERUNG ---
if "setup_done" not in st.session_state:
    st.session_state.update({
        "current_item": None,
        "attempts": 0,
        "answered": False,
        "feedback_msg": None,
        "feedback_type": None,
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": [],
        "setup_done": True
    })

# --- SIDEBAR ---
st.sidebar.title("🇨🇭 Wappen-Trainer")
if not df.empty:
    anzahl = len(df)
    st.sidebar.metric("Erfasste Gemeinden", f"{anzahl} / 2131")
    st.sidebar.progress(min(anzahl / 2131, 1.0))

st.sidebar.divider()
mode = st.sidebar.radio("Modus wählen", ["Lernen", "Quiz"])

def next_question(kanton_filter=None):
    st.session_state.feedback_msg = None
    st.session_state.answered = False
    st.session_state.attempts = 0
    
    if mode == "Lernen":
        pool = df[df['kanton'] == kanton_filter] if kanton_filter else df
        if not pool.empty:
            st.session_state.current_item = pool.sample(1).iloc[0].to_dict()
    else:
        if st.session_state.quiz_queue:
            st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        else:
            st.session_state.current_item = None

# --- STEUERUNG ---
if mode == "Lernen":
    kantone = sorted(df['kanton'].unique()) if not df.empty else []
    k_wahl = st.sidebar.selectbox("Kanton wählen", kantone if kantone else ["Keine Daten"])
    if st.sidebar.button("Nächstes Wappen"):
        next_question(k_wahl)
        st.rerun()
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
    
    if mode == "Quiz":
        s = st.session_state.quiz_stats
        beantw = s['correct'] + s['wrong']
        st.subheader(f"Frage {beantw + 1} von {s['total']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Richtig", s['correct'])
        c2.metric("Falsch", s['wrong'])
        q = (s['correct'] / beantw * 100) if beantw > 0 else 0
        c3.metric("Quote", f"{q:.1f}%")

    if os.path.exists(str(item.get('bild_pfad', ''))):
        st.image(item['bild_pfad'], width=300)
    
    if mode == "Lernen" and not st.session_state.answered and st.session_state.attempts > 0:
        st.info(get_hint(name_richtig, st.session_state.attempts))

    if st.session_state.feedback_msg:
        if st.session_state.feedback_type == "success": st.success(st.session_state.feedback_msg)
        elif st.session_state.feedback_type == "error": st.error(st.session_state.feedback_msg)
        else: st.warning(st.session_state.feedback_msg)

    user_input = st.text_input("Name der Gemeinde:", key=f"in_{name_richtig}", disabled=st.session_state.answered)

    if not st.session_state.answered and st.button("Prüfen"):
        score = fuzz.ratio(user_input.lower().strip(), name_richtig.lower().strip())
        if score == 100:
            st.session_state.feedback_msg = f"Korrekt! Es ist {name_richtig}."
            st.session_state.feedback_type = "success"
            if mode == "Quiz": st.session_state.quiz_stats['correct'] += 1
            st.session_state.answered = True
        else:
            if mode == "Lernen":
                st.session_state.attempts += 1
                if st.session_state.attempts >= 3:
                    st.session_state.feedback_msg = f"Lösung: {name_richtig}"
                    st.session_state.feedback_type = "error"
                    st.session_state.answered = True
                else:
                    st.session_state.feedback_msg = f"Falsch! (Versuch {st.session_state.attempts}/3)"
                    st.session_state.feedback_type = "warning"
            else:
                st.session_state.feedback_msg = f"Falsch! Richtig ist: {name_richtig}"
                st.session_state.feedback_type = "error"
                st.session_state.quiz_stats['wrong'] += 1
                st.session_state.quiz_stats['wrong_list'].append(item)
                st.session_state.answered = True
        st.rerun()
    
    if st.session_state.answered:
        if st.button("Nächstes Wappen ➡️"):
            next_question(k_wahl if mode == "Lernen" else None)
            st.rerun()

elif mode == "Quiz" and st.session_state.quiz_stats['total'] > 0:
    st.balloons()
    st.header("Quiz beendet!")
    s = st.session_state.quiz_stats
    st.write(f"Ergebnis: {s['correct']} von {s['total']} richtig.")
    if s['wrong_list'] and st.button("Fehler wiederholen"):
        st.session_state.quiz_queue = s['wrong_list'].copy()
        st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(s['wrong_list']), "wrong_list": []}
        next_question()
        st.rerun()
else:
    st.info("Wähle einen Kanton/Modus und klicke auf den Button!")
