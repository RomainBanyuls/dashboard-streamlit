import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 🚀 Configuration de la page
st.set_page_config(page_title="Dashboard Transport", layout="wide")

# 📌 Chargement des données depuis le fichier Parquet stocké sur GitHub
@st.cache_data
def load_data():
    df = pd.read_parquet("df_geo_v2.parquet")  # Lecture directe depuis GitHub
    return df

df = load_data()

# 📌 Sidebar - Filtres
st.sidebar.header("Filtres")
date_debut, date_fin = st.sidebar.date_input("Sélectionne une période", [df["DATE_DEPART"].min(), df["DATE_DEPART"].max()])
agence_enl = st.sidebar.multiselect("Agence d'Enlèvement", sorted(df["AGENCE_ENL"].unique()))
agence_liv = st.sidebar.multiselect("Agence de Livraison", sorted(df["AGENCE_LIV"].unique()))
produit = st.sidebar.multiselect("Produit", df["PRODUIT"].unique())
priorite = st.sidebar.multiselect("Priorité", df["PRIORITE"].unique())

# 📌 Application des filtres
df_filtered = df[(df["DATE_DEPART"] >= pd.to_datetime(date_debut)) & (df["DATE_DEPART"] <= pd.to_datetime(date_fin))]
if agence_enl:
    df_filtered = df_filtered[df_filtered["AGENCE_ENL"].isin(agence_enl)]
if agence_liv:
    df_filtered = df_filtered[df_filtered["AGENCE_LIV"].isin(agence_liv)]
if produit:
    df_filtered = df_filtered[df_filtered["PRODUIT"].isin(produit)]
if priorite:
    df_filtered = df_filtered[df_filtered["PRIORITE"].isin(priorite)]

# 📊 Scorecards avec encadrement et suppression des millisecondes
def format_timedelta(td):
    return str(td).split(".")[0]  # Supprime les millisecondes

st.markdown("### 📊 Indicateurs Clés")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Nombre d'OT", f"{len(df_filtered):,}")
with col2:
    st.metric("Nombre de Colis", f"{df_filtered['NB_COLIS'].sum():,}")
with col3:
    st.metric("Temps moyen DL_H", format_timedelta(df_filtered['DL_H'].mean()))

col4, col5, col6 = st.columns(3)
with col4:
    st.metric("Temps moyen DT_H", format_timedelta(df_filtered['DT_H'].mean()))
with col5:
    st.metric("Temps moyen DDK_H", format_timedelta(df_filtered['DDK_H'].mean()))
with col6:
    st.metric("Temps Retard Moyen", format_timedelta(df_filtered.loc[df_filtered['DELAIS_RETARD'] > pd.Timedelta(0), 'DELAIS_RETARD'].mean()))

# 📈 Indicateur cible + Gauge chart
st.subheader("🎯 Objectif de livraison à temps")
cible = st.slider("Cible : % OT livrés dans les temps", min_value=0.0, max_value=1.0, value=0.9, step=0.01)
percent_livres = 1 - df_filtered["RETARD"].mean()
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=percent_livres * 100,
    delta={'reference': cible * 100},
    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "blue"}},
    title={'text': "% OT livrés dans les temps"}
))
st.plotly_chart(fig_gauge, use_container_width=True)

# 📈 Graphique : Nombre d’OT par Priorité
st.subheader("📊 Nombre d'OT par Priorité")
df_priorite = df_filtered.groupby("PRIORITE")["OT"].count().reset_index()
fig1 = px.bar(df_priorite, x="PRIORITE", y="OT", title="Nombre d'OT par Priorité", text_auto=True)
st.plotly_chart(fig1, use_container_width=True)

# 📈 Graphique : Somme de POIDS_DECLARE et Nombre d'OT par jour
st.subheader("📈 Somme de POIDS_DECLARE et Nombre d'OT par jour")
df_grouped = df_filtered.groupby(df_filtered['DATE_DERNIER_EVNT'].dt.date).agg({
    'POIDS_DECLARE': 'sum',
    'OT': 'count'
}).reset_index()
df_grouped['DATE_DERNIER_EVNT'] = pd.to_datetime(df_grouped['DATE_DERNIER_EVNT'])
df_grouped = df_grouped.sort_values(by="DATE_DERNIER_EVNT")
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df_grouped['DATE_DERNIER_EVNT'],
    y=df_grouped['POIDS_DECLARE'],
    name="Somme de POIDS_DECLARE",
    marker_color='blue',
    opacity=0.7
))
fig.add_trace(go.Scatter(
    x=df_grouped['DATE_DERNIER_EVNT'],
    y=df_grouped['OT'],
    name="Nombre de OT",
    mode='lines+markers',
    yaxis='y2',
    line=dict(color='cyan', width=2)
))
fig.update_layout(
    title="Somme de POIDS_DECLARE et Nombre d'OT par jour",
    xaxis=dict(title="DATE_DERNIER_EVNT", tickangle=-45, range=[pd.to_datetime(date_debut), pd.to_datetime(date_fin)]),
    yaxis=dict(title="Somme de POIDS_DECLARE"),
    yaxis2=dict(
        title="Nombre de OT",
        overlaying='y',
        side='right'
    ),
    legend=dict(x=0, y=1.1),
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

st.success("Dashboard prêt ! 🚀")