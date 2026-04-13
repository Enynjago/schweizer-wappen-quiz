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
        # Zeige 'level' Anzahl an Buchstaben pro Wortteil
        hint_parts.append(p[:level] + "..." if len(p) > level else p)
    return "Tipp: " + "-".join(hint_parts)

# --- INITIALISIERUNG SESSION STATE ---
if "mode" not in st.session_state:
    st.session_state.update({
        "current_item": None,
        "attempts": 0,
        "answered": False,
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": []
    })

# --- SIDEBAR ---
# --- SIDEBAR & STATISTIK ---
st.sidebar.title("🇨🇭 Wappen-Trainer")

# Statistik berechnen (DIESE ZEILEN HABEN GEFEHLT)
anzahl_erfasst = len(df)
gesamtzahl_schweiz = 2131
prozent_erfasst = (anzahl_erfasst / gesamtzahl_schweiz) * 100

st.sidebar.metric("Erfasste Gemeinden", f"{anzahl_erfasst} / {gesamtzahl_schweiz}")
st.sidebar.progress(anzahl_erfasst / gesamtzahl_schweiz)
st.sidebar.write(f"Du hast **{prozent_erfasst:.1f}%** der Schweiz in deiner Liste!")

st.sidebar.divider()

# --- LOGIK: NÄCHSTES WAPPEN ---
def next_question():
    if mode == "Lernen":
        pool = df[df['kanton'] == kanton_wahl]
        if len(pool) > 10: pool = pool.sample(10) # Max 10 im Lernmodus
        st.session_state.current_item = pool.sample(1).iloc[0]
    else: # Quiz
        if st.session_state.quiz_queue:
            st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        else:
            st.session_state.current_item = None
    
    st.session_state.attempts = 0
    st.session_state.answered = False

# --- MODUS SETUP ---
if mode == "Lernen":
    kanton_wahl = st.sidebar.selectbox("Kanton lernen", sorted(df['kanton'].unique()))
    if st.sidebar.button("Lernsession starten / Neues Wappen"):
        next_question()
        st.rerun()

else: # QUIZ MODUS
    kanton_wahl = st.sidebar.selectbox("Quiz-Region", ["Alle"] + sorted(df['kanton'].unique().tolist()))
    if st.sidebar.button("Quiz starten"):
        pool = df if kanton_wahl == "Alle" else df[df['kanton'] == kanton_wahl]
        queue = pool.sample(frac=1).to_dict('records') # Zufällige Reihenfolge
        st.session_state.quiz_queue = queue
        st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(queue), "wrong_list": []}
        next_question()
        st.rerun()

# --- HAUPTBEREICH ---
if st.session_state.current_item:
    item = st.session_state.current_item
    
    # Quiz-Header Info
    if mode == "Quiz":
        stats = st.session_state.quiz_stats
        progress = (stats['correct'] + stats['wrong'])
        st.write(f"Frage {progress + 1} von {stats['total']}")
        cols = st.columns(3)
        cols[0].metric("Richtig", stats['correct'])
        cols[1].metric("Falsch", stats['wrong'])
        percent = (stats['correct'] / progress * 100) if progress > 0 else 0
        cols[2].metric("Quote", f"{percent:.1f}%")

    st.image(item['bild_pfad'], width=250)
    
    # Lernhilfe (Tipps)
    if mode == "Lernen" and st.session_state.attempts > 0:
        hint = get_hint(item['gemeinde'], st.session_state.attempts)
        st.info(hint)

    user_input = st.text_input("Gemeinde eingeben:", key=f"input_{item['gemeinde']}", disabled=st.session_state.answered)

    # BUTTONS
    if not st.session_state.answered:
        if st.button("Prüfen"):
            match = fuzz.ratio(user_input.lower(), item['gemeinde'].lower())
            
            if match == 100:
                st.success(f"Richtig! Es ist {item['gemeinde']}.")
                if mode == "Quiz": st.session_state.quiz_stats['correct'] += 1
                st.session_state.answered = True
            else:
                st.session_state.attempts += 1
                if mode == "Lernen":
                    if st.session_state.attempts >= 3:
                        st.error(f"Lösung: {item['gemeinde']}")
                        st.session_state.answered = True
                    else:
                        st.warning("Falsch! Ein Tipp wurde eingeblendet.")
                else: # Quiz Modus (nur 1 Versuch)
                    st.error(f"Falsch! Die richtige Antwort wäre {item['gemeinde']} gewesen.")
                    st.session_state.quiz_stats['wrong'] += 1
                    st.session_state.quiz_stats['wrong_list'].append(item)
                    st.session_state.answered = True
            st.rerun()
    
    # Nächstes Wappen erscheint erst NACH dem Prüfen
    if st.session_state.answered:
        if st.button("Nächstes Wappen ➡️"):
            next_question()
            st.rerun()

elif mode == "Quiz" and st.session_state.quiz_stats['total'] > 0:
    st.balloons()
    st.header("Quiz beendet!")
    s = st.session_state.quiz_stats
    st.write(f"Ergebnis: {s['correct']} von {s['total']} richtig.")
    
    if s['wrong_list']:
        st.subheader("Diese hattest du falsch:")
        for w in s['wrong_list']:
            st.write(f"- {w['gemeinde']} ({w['kanton']})")
        
        if st.button("Nur falsche Wappen nochmals prüfen"):
            st.session_state.quiz_queue = s['wrong_list'].copy()
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(s['wrong_list']), "wrong_list": []}
            next_question()
            st.rerun()
# Anzeige in der Sidebar
st.sidebar.metric("Erfasste Gemeinden", f"{anzahl_erfasst} / {gesamtzahl_schweiz}")
st.sidebar.progress(anzahl_erfasst / gesamtzahl_schweiz)
st.sidebar.write(f"Du hast **{prozent:.1f}%** der Schweiz geschafft!")

st.sidebar.divider()

st.sidebar.header("Navigation")
# Da du erst mal nur AG hast, filtern wir direkt oder lassen die Wahl
kanton_wahl = st.sidebar.selectbox("Kanton", ["AG"] if "AG" in df['kanton'].values else ["Alle"])

if st.sidebar.button("Nächstes Wappen ➡️"):
    pool = df[df['kanton'] == kanton_wahl] if kanton_wahl != "Alle" else df
    if not pool.empty:
        st.session_state.current_item = pool.sample(1).iloc[0]
        st.session_state.feedback = None
    st.rerun()

# --- HAUPTTEIL ---
if st.session_state.current_item is not None:
    item = st.session_state.current_item
    
    st.subheader("Welche Gemeinde ist das?")
    
    # Bild laden (lokaler Pfad aus deiner CSV)
    if os.path.exists(item['bild_pfad']):
        st.image(item['bild_pfad'], width=300)
    else:
        st.error(f"Bild nicht gefunden: {item['bild_pfad']}")
    
    user_input = st.text_input("Name der Gemeinde")
    
    if st.button("Prüfen"):
        score = fuzz.ratio(user_input.lower(), item['gemeinde'].lower())
        if score == 100:
            st.success(f"Korrekt! Das ist {item['gemeinde']}.")
        elif score > 80:
            st.warning(f"Fast! {item['gemeinde']} ist richtig.")
        else:
            st.error(f"Leider falsch. Das ist {item['gemeinde']}.")
else:
    st.info("Klicke auf 'Nächstes Wappen' in der Sidebar, um zu starten!")
