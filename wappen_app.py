import streamlit as st
import pandas as pd
import random
import os
from thefuzz import fuzz

# --- DATEN LADEN ---
@st.cache_data
def load_data():
    if os.path.exists("gemeinden.csv"):
        # sep=None und engine='python' lassen pandas das Trennzeichen automatisch erkennen
        df = pd.read_csv("gemeinden.csv", sep=None, engine='python')
        
        # Um sicherzugehen, dass Leerzeichen oder Grossschreibung in den Spaltennamen
        # keine Probleme machen, bereinigen wir diese hier:
        df.columns = [c.lower().strip() for c in df.columns]
        return df
    else:
        st.error("Datei 'gemeinden.csv' nicht gefunden!")
        return pd.DataFrame(columns=["gemeinde", "kanton", "bild_pfad"])

df = load_data()

# --- APP SETUP ---
st.set_page_config(page_title="Wappen-Meister AG", page_icon="🇨🇭")
st.title("🇨🇭 Wappen-Meister: Kanton Aargau")

if "current_item" not in st.session_state:
    st.session_state.current_item = None

# --- SIDEBAR ---
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
