import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Order Analytics", layout="wide")

# 🔠 Mappa eventId → Nome evento (modificabile liberamente)
event_names = {
    2: "Rimini Marathon",
    5: "Champions Pulcini",
    9: "Nova Eroica Prosecco Hills",
    10: "Cinquanta KM Romagna",
    11: "Bulls Game",
    13: "Triathlon Caorle",
    14: "GF Squali",
    15: "Nove Colli",
    16: "Oceanman Cattolica"
}

st.sidebar.header("🔍 Filtro dati")
uploaded_file = st.sidebar.file_uploader("Carica file Excel degli ordini", type=["xlsx"])

if uploaded_file:
    # Legge entrambi i fogli Excel
    df_orders = pd.read_excel(uploaded_file, sheet_name="Orders")
    df_searches = pd.read_excel(uploaded_file, sheet_name="Searches")

    if "eventId" not in df_orders.columns or "amount" not in df_orders.columns or "stateId" not in df_orders.columns:
        st.error("Il foglio Orders non contiene le colonne necessarie: 'eventId', 'amount', 'stateId'")
    elif "event_id" not in df_searches.columns or "unique_users_count" not in df_searches.columns:
        st.error("Il foglio Searches non contiene le colonne necessarie: 'event_id', 'unique_users_count'")
    else:
        # Aggiungi colonna nome evento
        df_orders["eventName"] = df_orders["eventId"].map(event_names).fillna(df_orders["eventId"].astype(str))

        # Mappa anche gli ID degli eventi nel foglio Searches
        df_searches["eventName"] = df_searches["event_id"].map(event_names).fillna(df_searches["event_id"].astype(str))

        # Filtri evento
        with st.sidebar:
            st.header("🎛️ Filtro Eventi")
            selected_events = st.multiselect(
                "📍 Seleziona uno o più eventi:",
                options=sorted(df_orders['eventName'].unique()),
                default=None
            )
            st.markdown("—" * 15)
            st.caption("💡 Suggerimento: seleziona un solo evento per una vista dedicata.")

        df = df_orders.copy()
        if selected_events:
            df = df[df['eventName'].isin(selected_events)]
            df_searches_filtered = df_searches[df_searches['eventName'].isin(selected_events)]
        else:
            df_searches_filtered = df_searches
        
        if selected_events and len(selected_events) == 1:
            st.title(f"📦 {selected_events[0]} - Orders")
        else:
            st.title("📦 Order Analytics Dashboard")

        # Separazione confermati / abbandonati
        confirmed = df[df['stateId'] != 1]
        cart_users = df[df['stateId'] == 1]

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

            # Aggiunta spaziatura
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # Grafico a grandezza massima per andamento giornaliero acquisti
            st.markdown("## 📈 Andamento Giornaliero Acquisti")
            
            confirmed['date'] = pd.to_datetime(confirmed['datePayment'], errors='coerce').dt.date
            date_df = confirmed.dropna(subset=['date'])

            # Verifica se siamo in modalità singolo evento o multi-evento
            if selected_events and len(selected_events) == 1:
                # Singolo evento - mostra solo il totale
                amount_by_date = (
                    date_df
                    .groupby('date')['amount']
                    .sum()
                    .reset_index()
                )
                
                fig_daily = px.line(
                    amount_by_date,
                    x='date',
                    y='amount',
                    title="Andamento Giornaliero Acquisti",
                    labels={
                        'date': 'Giorni',
                        'amount': 'Acquisti (€)'
                    }
                )
            else:
                # Multi-evento - mostra la divisione per evento
                amount_by_date_event = (
                    date_df
                    .groupby(['date', 'eventName'])['amount']
                    .sum()
                    .reset_index()
                )
                
                fig_daily = px.line(
                    amount_by_date_event,
                    x='date',
                    y='amount',
                    color='eventName',
                    title="Andamento Giornaliero Acquisti",
                    labels={
                        'date': 'Giorni',
                        'amount': 'Acquisti (€)',
                        'eventName': 'Evento'
                    }
                )
            
            fig_daily.update_layout(
                height=500,
                title_font=dict(size=24),
                xaxis_title_font=dict(size=16),
                yaxis_title_font=dict(size=16)
            )
            
            st.plotly_chart(fig_daily, use_container_width=True)
            
            # Spaziatura dopo il grafico grande
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Riga con grafico Pareto e metriche
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("### 📊 Analisi Pareto")
                
                # Recupera i dati necessari per il grafico Pareto dai dati corretti nel foglio Searches
                selfies_count = 0
                unique_users = 0
                cart_users_count = 0
                purchases_count = 0
                complete_packages = 0
                
                if not df_searches_filtered.empty:
                    for event_id in df['eventId'].unique():
                        event_data = df_searches_filtered[df_searches_filtered['event_id'] == event_id]
                        
                        if not event_data.empty:
                            # Aggiungi i valori dalle colonne corrette nel foglio Searches
                            selfies_count += event_data['total_users_count'].sum()
                            unique_users += event_data['unique_users_count'].sum()
                            cart_users_count += event_data['total_orders_users'].sum()
                            purchases_count += event_data['total_orders'].sum()
                            complete_packages += event_data['total_allphotos'].sum()
                
                # Assumiamo che i pacchetti completi siano quelli con importo superiore a una certa soglia (da personalizzare)
                # complete_packages = len(confirmed[confirmed['amount'] > 50])  # esempio di soglia
                
                # Dati per il grafico Pareto
                categories = ['Selfie', 'Utenti Unici', 'Utenti al Carrello', 'Acquisti', 'Pacchetti Completi']
                values = [selfies_count, unique_users, cart_users_count, purchases_count, complete_packages]
                
                # Calcola la percentuale cumulativa
                cum_pct = values / selfies_count * 100
                
                # Crea il grafico Pareto
                fig_pareto = go.Figure()
                
                # Aggiungi le barre
                fig_pareto.add_trace(go.Bar(
                    x=categories,
                    y=values,
                    name='Valore',
                    marker_color='royalblue'
                ))
                
                # Aggiungi la linea per la percentuale cumulativa
                fig_pareto.add_trace(go.Scatter(
                    x=categories,
                    y=cum_pct,
                    mode='lines+markers',
                    name='%',
                    yaxis='y2',
                    line=dict(color='firebrick', width=2),
                    marker=dict(size=8)
                ))
                
                # Layout
                fig_pareto.update_layout(
                    title="Analisi Pareto",
                    xaxis=dict(title='Categoria'),
                    yaxis=dict(title='Conteggio', side='left'),
                    yaxis2=dict(
                        title='%',
                        side='right',
                        overlaying='y',
                        tickmode='linear',
                        tick0=0,
                        dtick=20,
                        range=[0, 100]
                    ),
                    legend=dict(x=0.7, y=1.0),
                    height=400
                )
                
                st.plotly_chart(fig_pareto, use_container_width=True)
            
            with col2:
                st.markdown("### 📌 Metriche Chiave")
                
                # Calcola il tasso di conversione usando i dati corretti dal foglio Searches
                conversion_rate = (purchases_count / unique_users * 100) if unique_users > 0 else 0
                
                # Mostro le metriche principali
                st.markdown("#### Acquisti e Conversione")
                metric_col1, metric_col2 = st.columns(2)
                
                with metric_col1:
                    st.metric("# Acquisti", f"{purchases_count}")
                    st.metric("# Pacchetti", f"{complete_packages}")
                
                with metric_col2:
                    st.metric("Conversion Rate", f"{conversion_rate:.2f}%")
                    st.metric("Utenti Unici", f"{unique_users}")
                
                # Un po' di spaziatura
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Calcola il valore utente
                user_value = total_amount / unique_users if unique_users > 0 else 0
                
                st.markdown("#### Valore e Spesa")
                metric_col3, metric_col4 = st.columns(2)
                
                with metric_col3:
                    st.metric("Spesa Media", f"{avg_amount:.2f}€")
                
                with metric_col4:
                    st.metric("Valore Utente", f"{user_value:.2f}€")
            
            # Spaziatura
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Riga finale con spesa media e grafico a torta
            col3, col4 = st.columns([1, 1])
            
            with col3:
                st.markdown("### 📈 Analisi per Evento")
            
                # Aggiungi il selettore per la metrica
                metric_to_plot = st.selectbox(
                    "Seleziona la metrica da visualizzare:",
                    options=["Spesa Media", "Valore Utente"]
                )
            
                if metric_to_plot == "Spesa Media":
                    avg_by_event = confirmed.groupby('eventName')['amount'].mean().reset_index()
                    y_col = 'amount'
                    title = "Media Ordini Confermati per Evento"
                    y_label = "Spesa Media (€)"
                else:
                    avg_by_event = confirmed.groupby('eventName').apply(
                        lambda x: x['amount'].sum() / x['unique_users_count'].sum() if x['unique_users_count'].sum() > 0 else 0
                    ).reset_index(name='user_value')
                    y_col = 'user_value'
                    title = "Valore Utente per Evento"
                    y_label = "Valore Utente (€)"
            
                fig_avg = px.bar(
                    avg_by_event,
                    x='eventName',
                    y=y_col,
                    title=title,
                    labels={
                        'eventName': 'Evento',
                        y_col: y_label
                    },
                    color='eventName'
                )
                st.plotly_chart(fig_avg, use_container_width=True)


            with col4:
                st.markdown("### 🍰 Distribuzione Acquisti per Prezzo")
                
                # Crea fasce di prezzo
                bins = [0, 10, 20, 30, 40, 50, float('inf')]
                labels = ['0-10€', '11-20€', '21-30€', '31-40€', '41-50€', '>50€']
                
                confirmed['price_range'] = pd.cut(confirmed['amount'], bins=bins, labels=labels)
                
                price_distribution = confirmed['price_range'].value_counts().reset_index()
                price_distribution.columns = ['price_range', 'count']
                
                fig_pie = px.pie(
                    price_distribution,
                    names='price_range',
                    values='count',
                    title="Distribuzione Acquisti per Fasce di Prezzo",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                
                fig_pie.update_layout(
                    font=dict(family="Arial, sans-serif", size=12),
                    title_font=dict(size=16),
                    title_x=0.5,
                    legend_title="Fascia di Prezzo"
                )
                
                fig_pie.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    pull=[0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03]
                )
                
                st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 📋 Dettaglio Ordini Confermati")
            st.dataframe(
                confirmed.drop(columns=['paymentResult','dateSaveUrl','userId','datePayment','price_range',"hashId",
                                        "note","paymentId"], errors='ignore'),
                use_container_width=True,
                height=500
            )
else:
    st.info("Carica un file Excel per iniziare.")
