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
        "user_guess": "",
        "q_answered": False,
        "q_feedback": None,
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
    st.sidebar.metric("Erfasste Gemeinden", f"{len(df)} / 2131")

st.sidebar.divider()
mode = st.sidebar.radio("Modus wählen", ["Lernen (Anki + Tippen)", "Quiz (Strenge Prüfung)"])

def next_question(kanton_filter=None):
    st.session_state.q_answered = False
    st.session_state.q_feedback = None
    st.session_state.show_solution = False
    st.session_state.user_guess = ""
    
    if mode == "Lernen (Anki + Tippen)":
        pool = df[df['kanton'] == kanton_filter] if kanton_filter else df
        if not pool.empty:
            st.session_state.current_item = pool.sample(1).iloc[0].to_dict()
    else:
        if st.session_state.quiz_queue:
            st.session_state.current_item = st.session_state.quiz_queue.pop(0)
            st.session_state.quiz_finished = False
        else:
            st.session_state.current_item = None
            st.session_state.quiz_finished = True

# --- STEUERUNG ---
if mode == "Lernen (Anki + Tippen)":
    st.session_state.quiz_active = False
    st.session_state.quiz_finished = False
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
            st.session_state.last_pool = pool.to_dict('records')
            st.session_state.quiz_queue = pool.sample(frac=1).to_dict('records')
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.quiz_active = True
            st.session_state.quiz_finished = False
            next_question()
            st.rerun()

# --- HAUPTBEREICH ---
if mode == "Lernen (Anki + Tippen)" and st.session_state.current_item:
    item = st.session_state.current_item
    name_richtig = str(item.get('gemeinde', ''))
    st.subheader("Lernmodus: Aktiv erinnern")
    if os.path.exists(str(item.get('bild_pfad', ''))):
        st.image(item['bild_pfad'], width=300)
    
    if not st.session_state.show_solution:
        st.session_state.user_guess = st.text_input("Überlege kurz: Wie heißt diese Gemeinde?", key="learn_input")
        if st.button("Lösung aufdecken"):
            st.session_state.show_solution = True
            st.rerun()
    else:
        st.markdown(f"### Lösung: **{name_richtig}**")
        if st.session_state.user_guess:
            st.write(f"Dein Tipp war: *{st.session_state.user_guess}*")
        c1, c2, c3 = st.columns(3)
        if c1.button("❌ Nicht gewusst"): next_question(k_wahl); st.rerun()
        if c2.button("✅ Gewusst"): next_question(k_wahl); st.rerun()
        if c3.button("⭐ Ganz einfach"): next_question(k_wahl); st.rerun()

elif mode == "Quiz (Strenge Prüfung)" and st.session_state.quiz_active:
    # --- FALL A: QUIZ LÄUFT NOCH ---
    if not st.session_state.quiz_finished and st.session_state.current_item:
        item = st.session_state.current_item
        name_richtig = str(item.get('gemeinde', ''))
        s = st.session_state.quiz_stats
        beantw = s['correct'] + s['wrong']
        
        st.subheader(f"Frage {beantw + 1} von {s['total']}")
        cols = st.columns(3)
        cols[0].metric("Richtig", s['correct'])
        cols[1].metric("Falsch", s['wrong'])
        quote = (s['correct'] / beantw * 100) if beantw > 0 else 0
        cols[2].metric("Quote", f"{quote:.1f}%")

        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=300)

        if st.session_state.q_feedback:
            if "Korrekt" in st.session_state.q_feedback: st.success(st.session_state.q_feedback)
            else: st.error(st.session_state.q_feedback)

        user_input = st.text_input("Name der Gemeinde:", key=f"q_in_{name_richtig}", disabled=st.session_state.q_answered)
        
        if not st.session_state.q_answered:
            if st.button("Prüfen"):
                if user_input.lower().strip() == name_richtig.lower().strip():
                    st.session_state.q_feedback = f"Korrekt! Das ist {name_richtig}."
                    st.session_state.quiz_stats['correct'] += 1
                else:
                    st.session_state.q_feedback = f"Falsch! Die richtige Lösung ist: {name_richtig}"
                    st.session_state.quiz_stats['wrong'] += 1
                    st.session_state.quiz_stats['wrong_list'].append(item)
                st.session_state.q_answered = True
                st.rerun()
        else:
            if st.button("Nächstes Wappen ➡️"):
                next_question()
                st.rerun()

    # --- FALL B: QUIZ IST FERTIG (ERGEBNISSE) ---
    else:
        st.balloons()
        st.header("Quiz abgeschlossen! 🎉")
        s = st.session_state.quiz_stats
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Gesamt", s['total'])
        c2.metric("Richtig", s['correct'])
        c3.metric("Falsch", s['wrong'])
        
        final_quote = (s['correct'] / s['total'] * 100) if s['total'] > 0 else 0
        st.write(f"### Erfolgsquote: **{final_quote:.1f}%**")
        
        st.divider()
        st.subheader("Wiederholung")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🔄 Alles nochmals"):
                st.session_state.quiz_queue = random.sample(st.session_state.last_pool, len(st.session_state.last_pool))
                st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
                st.session_state.quiz_finished = False
                next_question()
                st.rerun()
        
        with col_btn2:
            if s['wrong_list']:
                if st.button(f"🎯 Nur Fehler ({len(s['wrong_list'])})"):
                    # WICHTIG: Wir kopieren die Fehlerliste in die Queue
                    st.session_state.quiz_queue = random.sample(s['wrong_list'], len(s['wrong_list']))
                    st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
                    st.session_state.quiz_finished = False
                    st.session_state.quiz_active = True # Sicherstellen, dass Quiz aktiv bleibt
                    next_question()
                    st.rerun()
            else:
                st.success("Keine Fehler vorhanden!")

else:
    st.info("Bitte wähle eine Region und klicke auf 'Quiz starten'.")
