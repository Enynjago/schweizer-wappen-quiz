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
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": [],
        "setup_done": True
    })

# --- SIDEBAR & STATISTIK ---
st.sidebar.title("🇨🇭 Wappen-Trainer")

anzahl_erfasst = len(df)
gesamtzahl_schweiz = 2131
prozent_erfasst = (anzahl_erfasst / gesamtzahl_schweiz) * 100 if gesamtzahl_schweiz > 0 else 0

st.sidebar.metric("Erfasste Gemeinden", f"{anzahl_erfasst} / {gesamtzahl_schweiz}")
st.sidebar.progress(min(prozent_erfasst / 100, 1.0))
st.sidebar.write(f"Fortschritt: **{prozent_erfasst:.1f}%**")

st.sidebar.divider()
mode = st.sidebar.radio("Modus wählen", ["Lernen", "Quiz"])

# --- LOGIK: NÄCHSTES WAPPEN ---
def next_question(kanton_filter=None):
    if mode == "Lernen":
        pool = df[df['kanton'] == kanton_filter] if kanton_filter else df
        if not pool.empty:
            # Im Lernmodus wählen wir immer ein zufälliges aus dem Pool
            st.session_state.current_item = pool.sample(1).iloc[0].to_dict()
    else: # Quiz
        if st.session_state.quiz_queue:
            st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        else:
            st.session_state.current_item = None
    
    st.session_state.attempts = 0
    st.session_state.answered = False

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
        aktuell = s['correct'] + s['wrong'] + 1
        st.subheader(f"Frage {aktuell} von {s['total']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Richtig", s['correct'])
        c2.metric("Falsch", s['wrong'])
        beantwortet = s['correct'] + s['wrong']
        quote = (s['correct'] / beantwortet * 100) if beantwortet > 0 else 0
        c3.metric("Quote", f"{quote:.1f}%")

    # Wappen anzeigen
    if os.path.exists(item['bild_pfad']):
        st.image(item['bild_pfad'], width=300)
    else:
        st.warning(f"Bilddatei nicht gefunden: {item['bild_pfad']}")

    # Tipps & Lösungsanzeige (Lernmodus)
    if mode == "Lernen":
        if st.session_state.attempts == 1:
            st.info(get_hint(item['gemeinde'], 1))
        elif st.session_state.attempts == 2:
            st.info(get_hint(item['gemeinde'], 2))
        elif st.session_state.attempts >= 3 and not st.session_state.answered:
            st.error(f"Nicht ganz! Die richtige Lösung ist: **{item['gemeinde']}**")
            st.session_state.answered = True # Beendet die Eingabe für dieses Wappen

    # Eingabefeld
    user_input = st.text_input("Wie heisst diese Gemeinde?", key=f"input_{item['gemeinde']}", disabled=st.session_state.answered)

    if not st.session_state.answered:
        if st.button("Prüfen"):
            score = fuzz.ratio(user_input.lower().strip(), item['gemeinde'].lower().strip())
            
            if score == 100:
                st.success(f"Korrekt! Das ist {item['gemeinde']}.")
                if mode == "Quiz": st.session_state.quiz_stats['correct'] += 1
                st.session_state.answered = True
            else:
                st.session_state.attempts += 1
                if mode == "Lernen":
                    if st.session_state.attempts < 3:
                        st.warning(f"Falsch! Versuch {st.session_state.attempts}/3. Ein Tipp wurde oben eingeblendet.")
                else: # Quizmodus: Sofort fertig
                    st.error(f"Falsch! Die richtige Antwort ist: {item['gemeinde']}")
                    st.session_state.quiz_stats['wrong'] += 1
                    st.session_state.quiz_stats['wrong_list'].append(item)
                    st.session_state.answered = True
            st.rerun()
    
    # "Nächstes Wappen" erscheint nach Prüfung oder nach 3 Fehlversuchen
    if st.session_state.answered:
        if st.button("Nächstes Wappen ➡️"):
            if mode == "Lernen":
                next_question(kanton_wahl)
            else:
                next_question()
            st.rerun()

elif mode == "Quiz" and st.session_state.quiz_stats['total'] > 0:
    st.balloons()
    st.header("Quiz abgeschlossen!")
    s = st.session_state.quiz_stats
    st.write(f"Ergebnis: **{s['correct']} von {s['total']}** richtig.")
    
    if s['wrong_list']:
        st.subheader("Diese Gemeinden musst du noch üben:")
        for w in s['wrong_list']:
            st.write(f"• {w['gemeinde']} ({w['kanton']})")
        
        if st.button("Nur die falschen Wappen nochmals prüfen"):
            st.session_state.quiz_queue = s['wrong_list'].copy()
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(s['wrong_list']), "wrong_list": []}
            next_question()
            st.rerun()
else:
    st.info("Willkommen! Wähle links einen Kanton und klicke auf 'Start', um loszulegen.")
