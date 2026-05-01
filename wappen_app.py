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
        "last_feedback": "", 
        "quiz_active": False,
        "quiz_finished": False,
        "last_pool": [],
        "quiz_stats": {"correct": 0, "wrong": 0, "total": 0, "wrong_list": []},
        "quiz_queue": [],
        "setup_done": True
    })

# --- FUNKTIONEN ---
def next_question():
    st.session_state.show_solution = False
    st.session_state.q_answered = False
    st.session_state.user_guess = ""
    if st.session_state.quiz_queue:
        st.session_state.current_item = st.session_state.quiz_queue.pop(0)
        st.session_state.quiz_finished = False
    else:
        st.session_state.current_item = None
        st.session_state.quiz_finished = True

def render_image(path_str):
    if not path_str or pd.isna(path_str):
        st.warning("Kein Bild verfügbar.")
        return
    paths = [p.strip() for p in str(path_str).split(",")]
    chosen = random.choice(paths)
    if os.path.exists(chosen):
        st.image(chosen, width=300)
    else:
        st.error(f"Datei nicht gefunden: {chosen}")

# --- QUIZ-LOGIK FUNKTION (LÖSCHT DAS FELD NACH ENTER) ---
def check_answer():
    # Wert aus dem Feld holen
    user_val = st.session_state.quiz_input.strip()
    item = st.session_state.current_item
    
    if user_val and item:
        correct_name = item['gemeinde'].strip()
        if user_val.lower() == correct_name.lower():
            st.session_state.quiz_stats['correct'] += 1
            st.session_state.last_feedback = f"✅ Richtig: {correct_name}"
            st.toast(f"Korrekt! 🎉", icon="✅")
        else:
            st.session_state.quiz_stats['wrong'] += 1
            st.session_state.quiz_stats['wrong_list'].append(item)
            st.session_state.last_feedback = f"❌ Falsch! Richtig war: {correct_name}"
            st.toast(f"Leider falsch...", icon="❌")
        
        # DAS GEHEIMNIS: Feld im Session State leeren
        st.session_state.quiz_input = ""
        # Zum nächsten Wappen springen
        next_question()

# --- SIDEBAR ---
st.sidebar.title("🇨🇭 Wappen-Trainer")
if not df.empty:
    st.sidebar.metric("Erfasste Gemeinden", f"{len(df)} / 2121")

st.sidebar.divider()
mode = st.sidebar.radio("Modus wählen", ["Lernen (Anki + Tippen)", "Quiz (Strenge Prüfung)"])

if mode == "Quiz (Strenge Prüfung)":
    kantone_liste = sorted(df['kanton'].unique().tolist()) if not df.empty else []
    ausgewaehlte_kantone = st.sidebar.multiselect("Kantone wählen (leer = alle):", options=kantone_liste)
    
    if st.sidebar.button("Quiz starten"):
        pool_df = df[df['kanton'].isin(ausgewaehlte_kantone)] if ausgewaehlte_kantone else df
        if not pool_df.empty:
            pool = pool_df.to_dict('records')
            st.session_state.last_pool = pool
            st.session_state.quiz_queue = random.sample(pool, len(pool))
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(pool), "wrong_list": []}
            st.session_state.last_feedback = ""
            st.session_state.quiz_active = True
            st.session_state.quiz_finished = False
            next_question()
            st.rerun()

# --- HAUPTBEREICH ---
if mode == "Lernen (Anki + Tippen)":
    st.session_state.quiz_active = False
    kantone = sorted(df['kanton'].unique()) if not df.empty else []
    k_wahl = st.sidebar.selectbox("Kanton wählen", kantone, key="learn_kanton")
    
    if st.session_state.current_item is None or st.session_state.get('last_mode') != "Lernen":
        st.session_state.last_mode = "Lernen"
        pool = df[df['kanton'] == k_wahl] if not df.empty else pd.DataFrame()
        if not pool.empty:
            st.session_state.current_item = pool.sample(1).iloc[0].to_dict()

    if st.session_state.current_item:
        item = st.session_state.current_item
        st.subheader("Lernmodus")
        render_image(item.get('bild_pfad', ''))
        
        if not st.session_state.show_solution:
            st.text_input("Wie heißt diese Gemeinde?", key="l_in")
            if st.button("Lösung aufdecken"):
                st.session_state.show_solution = True
                st.rerun()
        else:
            st.markdown(f"### Lösung: **{item['gemeinde']}**")
            c1, c2, c3 = st.columns(3)
            if c1.button("❌ Nicht gewusst"):
                st.session_state.current_item = df[df['kanton'] == k_wahl].sample(1).iloc[0].to_dict()
                st.session_state.show_solution = False
                st.rerun()
            if c2.button("✅ Gewusst"):
                st.session_state.current_item = df[df['kanton'] == k_wahl].sample(1).iloc[0].to_dict()
                st.session_state.show_solution = False
                st.rerun()
            if c3.button("⭐ Ganz einfach"):
                st.session_state.current_item = df[df['kanton'] == k_wahl].sample(1).iloc[0].to_dict()
                st.session_state.show_solution = False
                st.rerun()

elif mode == "Quiz (Strenge Prüfung)" and st.session_state.quiz_active:
    if not st.session_state.quiz_finished and st.session_state.current_item:
        item = st.session_state.current_item
        s = st.session_state.quiz_stats
        
        aktuell = s['correct'] + s['wrong'] + 1
        st.subheader(f"Wappen {aktuell} von {s['total']}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Richtig", s['correct'])
        m2.metric("Falsch", s['wrong'])
        quote = (s['correct'] / (s['correct'] + s['wrong']) * 100) if (s['correct'] + s['wrong']) > 0 else 0
        m3.metric("Quote", f"{quote:.1f}%")
        
        if st.session_state.last_feedback:
            if "✅" in st.session_state.last_feedback:
                st.success(st.session_state.last_feedback)
            else:
                st.error(st.session_state.last_feedback)

        render_image(item.get('bild_pfad', ''))

        # Textfeld: Löscht sich jetzt selbst durch die check_answer Funktion
        st.text_input(
            "Gemeindename eingeben & ENTER:", 
            key="quiz_input", 
            on_change=check_answer
        )
        st.caption("Fokus liegt auf dem Feld: Tippen, Enter, nächstes Wappen.")

    elif st.session_state.quiz_finished:
        st.balloons()
        st.header("Quiz abgeschlossen!")
        s = st.session_state.quiz_stats
        st.write(f"### Ergebnis: {s['correct']} von {s['total']} richtig")
        
        st.divider()
        col_a, col_b = st.columns(2)
        
        if col_a.button("🔄 Alles wiederholen", use_container_width=True):
            st.session_state.quiz_queue = random.sample(st.session_state.last_pool, len(st.session_state.last_pool))
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.last_feedback = ""
            next_question()
            st.rerun()
            
        if s['wrong_list']:
            if col_b.button(f"🎯 Nur Fehler wiederholen ({len(s['wrong_list'])})", use_container_width=True):
                st.session_state.quiz_queue = random.sample(s['wrong_list'], len(s['wrong_list']))
                st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
                st.session_state.last_feedback = ""
                next_question()
                st.rerun()
else:
    st.info("Wähle links Kantone aus und starte das Training.")
