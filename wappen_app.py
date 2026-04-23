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

# --- SIDEBAR ---
st.sidebar.title("🇨🇭 Wappen-Trainer")
if not df.empty:
    st.sidebar.metric("Erfasste Gemeinden", f"{len(df)} / 2121")

st.sidebar.divider()
mode = st.sidebar.radio("Modus wählen", ["Lernen (Anki + Tippen)", "Quiz (Strenge Prüfung)"])

if mode == "Quiz (Strenge Prüfung)":
    # --- ÄNDERUNG HIER: MULTISELECT STATT SELECTBOX ---
    kantone_liste = sorted(df['kanton'].unique().tolist()) if not df.empty else []
    ausgewaehlte_kantone = st.sidebar.multiselect(
        "Kantone für Quiz auswählen:", 
        options=kantone_liste,
        default=None,
        help="Wähle einen oder mehrere Kantone. Wenn leer, werden alle Kantone abgefragt."
    )
    
    if st.sidebar.button("Quiz starten"):
        # Logik für den Pool: Wenn Kantone gewählt wurden, filtere danach. Sonst nimm alle.
        if ausgewaehlte_kantone:
            pool = df[df['kanton'].isin(ausgewaehlte_kantone)]
        else:
            pool = df
            
        if not pool.empty:
            st.session_state.last_pool = pool.to_dict('records')
            st.session_state.quiz_queue = pool.sample(frac=1).to_dict('records')
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            st.session_state.quiz_active = True
            st.session_state.quiz_finished = False
            next_question()
            st.rerun()

# --- HAUPTBEREICH (BLEIBT GLEICH) ---
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
        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=300)
        
        if not st.session_state.show_solution:
            st.session_state.user_guess = st.text_input("Wie heißt diese Gemeinde?", key="l_in")
            if st.button("Lösung aufdecken"):
                st.session_state.show_solution = True
                st.rerun()
        else:
            st.markdown(f"### Lösung: **{item['gemeinde']}**")
            if st.session_state.user_guess:
                st.write(f"Dein Tipp: *{st.session_state.user_guess}*")
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
        
        st.subheader(f"Frage {s['correct'] + s['wrong'] + 1} von {s['total']}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Richtig", s['correct'])
        col2.metric("Falsch", s['wrong'])
        perc = (s['correct']/(s['correct']+s['wrong'])*100) if (s['correct']+s['wrong']) > 0 else 0
        col3.metric("Quote", f"{perc:.1f}%")

        if os.path.exists(str(item.get('bild_pfad', ''))):
            st.image(item['bild_pfad'], width=300)

        user_input = st.text_input("Gemeindename:", key=f"q_{item['gemeinde']}", disabled=st.session_state.q_answered)
        
        if not st.session_state.q_answered:
            if st.button("Prüfen"):
                if user_input.lower().strip() == item['gemeinde'].lower().strip():
                    st.success(f"Korrekt! Das ist {item['gemeinde']}.")
                    st.session_state.quiz_stats['correct'] += 1
                else:
                    st.error(f"Falsch! Die richtige Lösung ist: {item['gemeinde']}")
                    st.session_state.quiz_stats['wrong'] += 1
                    st.session_state.quiz_stats['wrong_list'].append(item)
                st.session_state.q_answered = True
                st.rerun()
        else:
            if st.button("Nächstes Wappen ➡️"):
                next_question()
                st.rerun()

    elif st.session_state.quiz_finished:
        st.balloons()
        st.header("Quiz abgeschlossen!")
        s = st.session_state.quiz_stats
        st.write(f"### Ergebnis: {s['correct']} von {s['total']} richtig ({ (s['correct']/s['total']*100):.1f}%)")
        
        st.divider()
        c1, c2 = st.columns(2)
        if c1.button("🔄 Alles wiederholen", use_container_width=True):
            st.session_state.quiz_queue = random.sample(st.session_state.last_pool, len(st.session_state.last_pool))
            st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
            next_question()
            st.rerun()
        
        if s['wrong_list']:
            if c2.button(f"🎯 Nur Fehler wiederholen ({len(s['wrong_list'])})", use_container_width=True):
                st.session_state.quiz_queue = random.sample(st.session_state.wrong_list, len(st.session_state.wrong_list))
                st.session_state.quiz_stats = {"correct": 0, "wrong": 0, "total": len(st.session_state.quiz_queue), "wrong_list": []}
                next_question()
                st.rerun()
else:
    st.info("Wähle links Kantone aus und starte das Training.")
