import streamlit as st
import pandas as pd
import random
import os
from thefuzz import fuzz

# --- DATEN LADEN ---
@st.cache_data
def load_data():
    if os.path.exists("gemeinden.csv"):
        # Automatisches Erkennen von Trennzeichen (Semikolon-Support)
        df = pd.read_csv("gemeinden.csv", sep=None, engine='python')
        # Spaltennamen bereinigen
        df.columns = [c.lower().strip() for c in df.columns]
        return df
    return pd.DataFrame(columns=["gemeinde", "kanton", "bild_pfad"])

df = load_data()

# --- HILFSFUNKTION FÜR BUCHSTABEN-TIPPS ---
def get_hint(word, level):
    if level == 0: return ""
    # Erkennt Bindestriche und gibt für jeden Teil Tipps
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
    st.session_state.update({
        "current_item": None,
        "attempts": 0,
        "answered": False,
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": []
    })

# --- SIDEBAR & STATISTIK ---
st.sidebar.title("🇨🇭 Wappen-Trainer")

# Globale Statistik
anzahl_erfasst = len(df)
gesamtzahl_schweiz = 2131
prozent_erfasst = (anzahl_erfasst / gesamtzahl_schweiz) * 100 if gesamtzahl_schweiz > 0 else 0

st.sidebar.metric("Erfasste Gemeinden", f"{anzahl_erfasst} / {gesamtzahl_schweiz}")
st.sidebar.progress(min(prozent_erfasst / 100, 1.0))
st.sidebar.write(f"Du hast **{prozent_erfasst:.1f}%** der Schweiz erfasst.")

st.sidebar.divider()

# Modus wählen
mode = st.sidebar.radio("Modus wählen", ["Lernen", "Quiz"])

# --- LOGIK: NÄCHSTES WAPPEN ---
def next_question(kanton_filter=None):
    if mode == "Lernen":
        pool = df[df['kanton'] == kanton_filter]
        if not pool.empty:
            # Im Lernmodus wählen wir zufällig aus dem Pool
            st.session_state.current_item = pool.sample(1).iloc[0]
    else: # Quiz
        if st.session_state.quiz_queue:
            st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        else:
            st.session_state.current_item = None
    
    st.session_state.attempts = 0
    st.session_state.answered = False

# --- STEUERUNG JE NACH MODUS ---
if mode == "Lernen":
    kanton_wahl = st.sidebar.selectbox("Kanton lernen", sorted(df['kanton'].unique()) if not df.empty else ["Keine Daten"])
    if st.sidebar.button("Nächstes Wappen"):
        next_question(kanton_wahl)
        st.rerun()

else: # QUIZ MODUS
    kanton_wahl = st.sidebar.selectbox("Quiz-Region", ["Alle"] + sorted(df['kanton'].unique().tolist()) if not df.empty else ["Keine Daten"])
    if st.sidebar.button("Quiz starten"):
        pool = df if kanton_wahl == "Alle" else df[df['kanton'] == kanton_wahl]
        if not pool.empty:
            queue = pool.sample(frac=1).to_dict('records')
            st.session_state.quiz_queue = queue
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(queue), "wrong_list": []}
            next_question()
            st.rerun()

# --- HAUPTBEREICH ---
if st.session_state.current_item:
    item = st.session_state.current_item
    
    if mode == "Quiz":
        s = st.session_state.quiz_stats
        aktuell = s['correct'] + s['wrong'] + 1
        st.write(f"**Frage {aktuell} von {s['total']}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Richtig", s['correct'])
        c2.metric("Falsch", s['wrong'])
        quote = (s['correct'] / (aktuell-1) * 100) if (aktuell-1) > 0 else 0
        c3.metric("Quote", f"{quote:.1f}%")

    # Wappen anzeigen
    if os.path.exists(item['bild_pfad']):
        st.image(item['bild_pfad'], width=250)
    else:
        st.error(f"Bild nicht gefunden: {item['bild_pfad']}")

    # Lern-Tipps anzeigen
    if mode == "Lernen" and st.session_state.attempts > 0:
        st.info(get_hint(item['gemeinde'], st.session_state.attempts))

    # Eingabefeld
    user_input = st.text_input("Name der Gemeinde:", key=f"in_{item['gemeinde']}", disabled=st.session_state.answered)

    if not st.session_state.answered:
        if st.button("Prüfen"):
            # Vergleich (Fuzzy Matching für kleine Tippfehler)
            score = fuzz.ratio(user_input.lower().strip(), item['gemeinde'].lower().strip())
            
            if score == 100:
                st.success(f"Korrekt! Das ist {item['gemeinde']}.")
                if mode == "Quiz": st.session_state.quiz_stats['correct'] += 1
                st.session_state.answered = True
            else:
                st.session_state.attempts += 1
                if mode == "Lernen":
                    if st.session_state.attempts >= 3:
                        st.error(f"Lösung: {item['gemeinde']}")
                        st.session_state.answered = True
                    else:
                        st.warning("Falsch! Ein Tipp wurde oben eingeblendet.")
                else: # Quiz (nur 1 Versuch)
                    st.error(f"Falsch! Richtig wäre: {item['gemeinde']}")
                    st.session_state.quiz_stats['wrong'] += 1
                    st.session_state.quiz_stats['wrong_list'].append(item)
                    st.session_state.answered = True
            st.rerun()
    
    # Nächstes Wappen Button (erscheint erst nach Prüfung)
    if st.session_state.answered:
        if st.button("Nächstes Wappen ➡️"):
            if mode == "Lernen":
                next_question(kanton_wahl)
            else:
                next_question()
            st.rerun()

elif mode == "Quiz" and st.session_state.quiz_stats['total'] > 0:
    st.balloons()
    st.header("Quiz beendet!")
    s = st.session_state.quiz_stats
    st.write(f"Du hast {s['correct']} von {s['total']} Wappen richtig erkannt.")
    
    if s['wrong_list']:
        st.subheader("Diese Gemeinden musst du noch üben:")
        for w in s['wrong_list']:
            st.write(f"• {w['gemeinde']} ({w['kanton']})")
        
        if st.button("Nur falsche Wappen nochmals starten"):
            st.session_state.quiz_queue = s['wrong_list'].copy()
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(s['wrong_list']), "wrong_list": []}
            next_question()
            st.rerun()
else:
    st.info("Wähle einen Kanton und klicke auf den Button, um zu starten!")
