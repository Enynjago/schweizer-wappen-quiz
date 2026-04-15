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
    anzahl_aktuell = len(df)
    st.sidebar.metric("Erfasste Gemeinden", f"{anzahl_aktuell} / 2121")
    st.sidebar.progress(min(anzahl_aktuell / 2121, 1.0))

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
    st.subheader("Lernmodus")
    if os.path.exists(str(item.get('bild_pfad', ''))):
        st.image(item['bild_pfad'], width=300)
    
    if not st.session_state.show_solution:
        with st.form("learn_form", clear_on_submit=True):
            st.text_input("Name tippen...", key="l_in")
            if st.form_submit_button("Lösung zeigen (Enter)"):
                st.session_state.show_solution = True
                st.rerun()
    else:
        st.markdown(f"### Lösung: **{name_richtig}**")
        c1, c2, c3 = st.columns(3)
        if c1.button("❌ Nicht gewusst"): next_question(k_wahl); st.rerun()
        if c2.button("✅ Gewusst"): next_question(k_wahl); st.rerun()
        if c3.button("⭐ Ganz einfach"): next_question(k_wahl); st.rerun()

elif mode == "Quiz (Strenge Prüfung)" and st.session_state.quiz_active:
    if not st.session_state.quiz_finished and st.session_state.current_item:
        item = st.session_state.current_item
        name_richtig = str(item.get('gemeinde', ''))
        s = st.session_state.quiz_stats
        
        st.subheader(f"Frage {s['correct'] + s['wrong'] + 1} von {s['total']}")
        
        # Wappen
        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=300)

        # Feedback
        if st.session_state.q_feedback:
            if "Korrekt" in st.session_state.q_feedback: st.success(st.session_state.q_feedback)
            else: st.error(st.session_state.q_feedback)

        # Das "Ein-Feld-System" für Doppel-Enter
        with st.form("quiz_form", clear_on_submit=True):
            if not st.session_state.q_answered:
                u_input = st.text_input("Name der Gemeinde:", key="active_q")
                if st.form_submit_button("Prüfen (Enter)"):
                    if u_input.lower().strip() == name_richtig.lower().strip():
                        st.session_state.q_feedback = f"Korrekt! Das ist {name_richtig}."
                        st.session_state.quiz_stats['correct'] += 1
                    else:
                        st.session_state.q_feedback = f"Falsch! Lösung: {name_richtig}"
                        st.session_state.quiz_stats['wrong'] += 1
                        st.session_state.quiz_stats['wrong_list'].append(item)
                    st.session_state.q_answered = True
                    st.rerun()
            else:
                # Das Feld ist jetzt quasi der "Weiter-Knopf"
                st.text_input("Lösung steht oben.", value="Drücke Enter für weiter...", disabled=True)
                if st.form_submit_button("Nächstes Wappen ➡️"):
                    next_question()
                    st.rerun()

    else:
        # Ergebnis-Bildschirm
        st.balloons()
        st.header("Quiz abgeschlossen!")
        s = st.session_state.quiz_stats
        st.write(f"Richtig: {s['correct']} | Falsch: {s['wrong']}")
        
        if st.button("🔄 Alles wiederholen"):
            st.session_state.quiz_queue = random.sample(st.session_state.last_pool, len(st.session_state.last_pool))
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.quiz_finished = False
            next_question()
            st.rerun()
        
        if s['wrong_list'] and st.button(f"🎯 Nur Fehler ({len(s['wrong_list'])})"):
            st.session_state.quiz_queue = random.sample(s['wrong_list'], len(s['wrong_list']))
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.quiz_finished = False
            next_question()
            st.rerun()
else:
    st.info("Wähle links eine Region und klicke auf 'Quiz starten'.")
