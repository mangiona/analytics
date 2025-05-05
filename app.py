import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Order Analytics", layout="wide")

# 🔠 Mappa eventId → Nome evento (modificabile liberamente)
event_names = {
    2: "Rimini Marathon",
    5: "Champions Pulcini",
    6: "Nico Run",
    7: "Test FotoRavenna",
    8: "Test Endu",
    9: "Nova Eroica Prosecco Hills",
    10: "Cinquanta KM Romagna",
    11: "Bulls Game",
    12: "Colle Marathon",
    13: "Triathlon Caorle",
    14: "GF Squali",
    15: "Nove Colli",
    16: "Oceanman Cattolica",
    17: "Sviluppo R&D"
}

st.sidebar.header("🔍 Filtro dati")
uploaded_file = st.sidebar.file_uploader("Carica file CSV degli ordini", type=["csv"])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file)

    if "eventId" not in df_raw.columns or "amount" not in df_raw.columns or "stateId" not in df_raw.columns:
        st.error("Il file non contiene le colonne necessarie: 'eventId', 'amount', 'stateId'")
    else:
        # Aggiungi colonna nome evento
        df_raw["eventName"] = df_raw["eventId"].map(event_names).fillna(df_raw["eventId"].astype(str))

        # Filtri evento
        with st.sidebar:
            st.header("🎛️ Filtro Eventi")
            selected_events = st.multiselect(
                "📍 Seleziona uno o più eventi:",
                options=sorted(df_raw['eventName'].unique()),
                default=None
            )
            st.markdown("—" * 15)
            st.caption("💡 Suggerimento: seleziona un solo evento per una vista dedicata.")

        df = df_raw.copy()
        if selected_events:
            df = df[df['eventName'].isin(selected_events)]

        
        if selected_events and len(selected_events) == 1:
            st.title(f"📦 {selected_events[0]} - Orders")
        else:
            st.title("📦 Order Analytics Dashboard")

        # Separazione confermati / abbandonati
        confirmed = df[df['stateId'] == 4]
        abandoned = df[df['stateId'] != 4]

        if confirmed.empty:
            st.warning("Nessun ordine confermato trovato.")
        else:
            total_orders = len(confirmed)
            total_amount = confirmed['amount'].sum()
            avg_amount = confirmed['amount'].mean()

            st.markdown("## ✅ Panoramica Ordini Confermati")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="🧾 Ordini Confermati", value=total_orders)
            with col2:
                st.metric(label="💰 Totale", value=f"{total_amount:.2f}€")
            with col3:
                st.metric(label="📊 Media Ordine", value=f"{avg_amount:.2f}€")

            st.markdown("### 📈 Grafici Ordini (tutti gli stati)")
            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:
                pie_df = df['stateId'].value_counts().reset_index()
                pie_df.columns = ['stateId', 'count']
                fig_pie = px.pie(pie_df, names='stateId', values='count', title="Distribuzione Stati Ordine")
                st.plotly_chart(fig_pie, use_container_width=True)

            with col2:
                # 📆 Grafico solo su ordini confermati
                confirmed['date'] = pd.to_datetime(confirmed['datePayment'], errors='coerce').dt.date
                date_df = confirmed.dropna(subset=['date'])

                amount_by_date_event = (
                    date_df
                    .groupby(['date', 'eventName'])['amount']
                    .sum()
                    .reset_index()
                )

                fig_line = px.line(
                    amount_by_date_event,
                    x='date',
                    y='amount',
                    color='eventName',
                    title="📅 Importo Totale per Giorno (solo ordini confermati)"
                )
                st.plotly_chart(fig_line, use_container_width=True)

            col3, col4 = st.columns(2)

            with col3:
                avg_by_event = confirmed.groupby('eventName')['amount'].mean().reset_index()
                fig_avg = px.bar(
                    avg_by_event,
                    x='eventName',
                    y='amount',
                    title="Media Ordini Confermati per Evento",
                    color='eventName'
                )
                st.plotly_chart(fig_avg, use_container_width=True)

            with col4:
                fig_hist = px.histogram(
                    confirmed,
                    x='amount',
                    color='eventName',
                    nbins=30,
                    title="Distribuzione Importi Confermati"
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            st.markdown("### 📋 Dettaglio Ordini Confermati")
            st.dataframe(
                confirmed.drop(columns=['paymentResult'], errors='ignore'),
                use_container_width=True,
                height=400
            )
else:
    st.info("Carica un file CSV per iniziare.")
