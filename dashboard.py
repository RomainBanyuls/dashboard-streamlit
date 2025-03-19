import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
# 🚀 Configuration de la page
st.set_page_config(page_title="Dashboard Transport", layout="wide")

# 📌 Chargement des données depuis le fichier Parquet stocké sur Hugging Face
@st.cache_data
def load_data():
    try:
        df = pd.read_parquet("df_geo_v2.parquet")  # Chargement du fichier localement
        
        # Vérifier et convertir les dates si nécessaire
        date_cols = ["DATE_OT", "DATE_DEPART", "DATE_ARRIVEE", "DLL", "DATE_DERNIER_EVNT"]
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données : {e}")
        return pd.DataFrame()

df = load_data()

# Vérifier si le dataset est bien chargé
if df.empty:
    st.warning("⚠️ Les données n'ont pas pu être chargées. Vérifiez que le fichier `df_geo_v2.parquet` est bien dans Hugging Face Spaces.")
    st.stop()

# 📌 Sidebar - Filtres
st.sidebar.header("Filtres")
date_debut, date_fin = st.sidebar.date_input(
    "Sélectionne une période", 
    [df["DATE_DERNIER_EVNT"].min(), df["DATE_DERNIER_EVNT"].max()]
)

agence_enl = st.sidebar.multiselect("Agence d'Enlèvement", sorted(df["AGENCE_ENL"].dropna().unique()))
agence_liv = st.sidebar.multiselect("Agence de Livraison", sorted(df["AGENCE_LIV"].dropna().unique()))
produit = st.sidebar.multiselect("Produit", df["PRODUIT"].dropna().unique())
priorite = st.sidebar.multiselect("Priorité", df["PRIORITE"].dropna().unique())
pays_enl = st.sidebar.multiselect("Pays d'enlèvement", df["PAYS_ENL"].dropna().unique())
pays_liv = st.sidebar.multiselect("Pays de livraison", df["PAYS_LIV"].dropna().unique())
region_enl = st.sidebar.multiselect("Region d'enlèvement", df["REGION_ENL"].dropna().unique())
region_liv = st.sidebar.multiselect("Region de livraison", df["REGION_LIV"].dropna().unique())
dpt_enl = st.sidebar.multiselect("Département d'enlèvement", sorted(df["DPT_ENL"].dropna().unique()))
dpt_liv = st.sidebar.multiselect("Département de livraison", sorted(df["DPT_LIV"].dropna().unique()))

# 📌 Application des filtres
df_filtered = df[
    (df["DATE_DERNIER_EVNT"] >= pd.to_datetime(date_debut)) & 
    (df["DATE_DERNIER_EVNT"] <= pd.to_datetime(date_fin))
]

if agence_enl:
    df_filtered = df_filtered[df_filtered["AGENCE_ENL"].isin(agence_enl)]
if agence_liv:
    df_filtered = df_filtered[df_filtered["AGENCE_LIV"].isin(agence_liv)]
if produit:
    df_filtered = df_filtered[df_filtered["PRODUIT"].isin(produit)]
if priorite:
    df_filtered = df_filtered[df_filtered["PRIORITE"].isin(priorite)]
if pays_enl:
    df_filtered = df_filtered[df_filtered["PAYS_ENL"].isin(pays_enl)]
if pays_liv:
    df_filtered = df_filtered[df_filtered["PAYS_LIV"].isin(pays_liv)]
if region_enl:
    df_filtered = df_filtered[df_filtered["REGION_ENL"].isin(region_enl)]
if region_liv:
    df_filtered = df_filtered[df_filtered["REGION_LIV"].isin(region_liv)]
if dpt_enl:
    df_filtered = df_filtered[df_filtered["DPT_ENL"].isin(dpt_enl)]
if dpt_liv:
    df_filtered = df_filtered[df_filtered["DPT_LIV"].isin(dpt_liv)]

# Vérifier si le DataFrame est vide
if df_filtered.empty:
    st.warning("⚠️ Aucun résultat trouvé pour ces filtres.")
    st.stop()

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
    st.metric("Délai de livraison moyen", format_timedelta(df_filtered['DL_H'].mean()))

col4, col5, col6 = st.columns(3)
with col4:
    st.metric("Délai de traitement moyen", format_timedelta(df_filtered['DT_H'].mean()))
with col5:
    st.metric("Délai dernier km moyen", format_timedelta(df_filtered['DDK_H'].mean()))
with col6:
    st.metric("Temps Retard Moyen", format_timedelta(df_filtered.loc[df_filtered['DELAIS_RETARD'] > pd.Timedelta(0), 'DELAIS_RETARD'].mean()))

col7, col8, col9 = st.columns(3)
with col7:
    st.metric("Nombre d'OT livré à temps", f"{df_filtered['DELAIS_A_TPS'].gt(pd.Timedelta(0)).sum():,}")
with col8:
    ot_avant_13h = df_filtered[(df_filtered['DELAIS_A_TPS'].gt(pd.Timedelta(0))) & 
                               (df_filtered['LIV_AVANT_13H'] == 1)].shape[0]
    total_ot = df_filtered['RETARD'].count()
    
    if total_ot > 0:  # Vérification pour éviter la division par zéro
        pourcentage = round((ot_avant_13h / total_ot) * 100, 2)
    else:
        pourcentage = 0  # Ou une autre valeur par défaut

    st.metric("OT livré à temps avant 13h", f"{pourcentage}%")
with col9:
    st.metric("Nombre d'OT en retard", f"{df_filtered['DELAIS_RETARD'].gt(pd.Timedelta(0)).sum():,}")

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