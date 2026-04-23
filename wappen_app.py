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

        # --- FEEDBACK ANZEIGEN ---
        if st.session_state.q_answered:
            if st.session_state.get('last_result') == "correct":
                st.success(f"Korrekt! Das ist {item['gemeinde']}.")
            else:
                st.error(f"Falsch! Die richtige Lösung ist: {item['gemeinde']}")

        user_input = st.text_input("Gemeindename:", key=f"q_{item['gemeinde']}", disabled=st.session_state.q_answered)
        
        if not st.session_state.q_answered:
            if st.button("Prüfen"):
                if user_input.lower().strip() == item['gemeinde'].lower().strip():
                    st.session_state.last_result = "correct"
                    st.session_state.quiz_stats['correct'] += 1
                else:
                    st.session_state.last_result = "wrong"
                    st.session_state.quiz_stats['wrong'] += 1
                    st.session_state.quiz_stats['wrong_list'].append(item)
                st.session_state.q_answered = True
                st.rerun()
        else:
            if st.button("Nächstes Wappen ➡️"):
                # Ergebnis für die Anzeige zurücksetzen
                st.session_state.last_result = None 
                next_question()
                st.rerun()
