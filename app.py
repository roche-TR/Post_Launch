import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="CEETRIS Performance Portal", layout="wide", page_icon="📊")

SHEET_ID = "1zQ479JIC8mT8G5ZHDZ7uhl4yjKVJxETeiZf4BXiawdw"
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

@st.cache_resource
def init_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

sheet = init_connection()

@st.cache_data(ttl=30)
def get_access_keys():
    return pd.DataFrame(sheet.worksheet("access_keys").get_all_records())

@st.cache_data(ttl=30)
def get_kpi_config():
    return pd.DataFrame(sheet.worksheet("kpi_config").get_all_records())

@st.cache_data(ttl=30)
def get_kpi_actuals():
    return pd.DataFrame(sheet.worksheet("kpi_actuals").get_all_records())

def save_config(df):
    ws = sheet.worksheet("kpi_config")
    all_data = ws.get_all_records()
    ws_df = pd.DataFrame(all_data)
    headers = ws.row_values(1)
    
    updates = []
    for _, row in df.iterrows():
        mask = ws_df['id'] == row['id']
        if mask.any():
            row_idx = ws_df[mask].index[0] + 2
            # Weight
            weight_col = headers.index('weight') + 1
            updates.append({
                'range': gspread.utils.rowcol_to_a1(row_idx, weight_col),
                'values': [[row['weight']]]
            })
            # Target ayları
            for m in months:
                col_name = f"target_{m.lower()}"
                if col_name in headers:
                    col_idx = headers.index(col_name) + 1
                    updates.append({
                        'range': gspread.utils.rowcol_to_a1(row_idx, col_idx),
                        'values': [[row[col_name]]]
                    })
    if updates:
        ws.batch_update(updates)

def save_actuals(df):
    ws = sheet.worksheet("kpi_actuals")
    all_data = ws.get_all_records()
    ws_df = pd.DataFrame(all_data)
    headers = ws.row_values(1)
    
    updates = []
    for _, row in df.iterrows():
        mask = ws_df['id'] == row['id']
        if mask.any():
            row_idx = ws_df[mask].index[0] + 2
            for m in months:
                col_name = f"act_{m.lower()}"
                if col_name in headers:
                    col_idx = headers.index(col_name) + 1
                    updates.append({
                        'range': gspread.utils.rowcol_to_a1(row_idx, col_idx),
                        'values': [[row[col_name]]]
                    })
    if updates:
        ws.batch_update(updates)

if 'role' not in st.session_state:
    st.session_state.update({
        'auth': False, 'country': None, 'product': None,
        'role': 'USER', 'user_title': None
    })

if not st.session_state.auth:
    st.title("🛡️ Post Launch Performance - Executive Portal")
    token = st.text_input("Access Token:", type="password").strip()
    if st.button("Authorize"):
        if token == "CEET-HEAD":
            st.session_state.update({
                'auth': True, 'role': 'ADMIN',
                'country': 'CEETRIS', 'product': 'ALL',
                'user_title': 'Head of CEETRIS'
            })
            st.balloons()
            st.rerun()
        elif token.endswith("-VIP"):
            df_keys = get_access_keys()
            res = df_keys[df_keys['secret_code'] == token]
            if not res.empty:
                st.session_state.update({
                    'auth': True, 'role': 'ADMIN',
                    'country': res.iloc[0]['country_label'],
                    'product': 'ALL',
                    'user_title': f"GM of {res.iloc[0]['country_label']}"
                })
                st.snow()
                st.rerun()
            else:
                st.error("❌ Invalid Token!")
        elif token:
            df_keys = get_access_keys()
            res = df_keys[df_keys['secret_code'] == token]
            if not res.empty:
                st.session_state.update({
                    'auth': True, 'role': 'USER',
                    'country': res.iloc[0]['country_label'],
                    'product': res.iloc[0]['product_name']
                })
                st.rerun()
            else:
                st.error("❌ Invalid Token!")
    st.stop()

if st.session_state.role == "ADMIN":
    st.sidebar.markdown(f"## 🏆 Welcome\n**{st.session_state.user_title}**")
    st.sidebar.divider()
    if st.session_state.country == "CEETRIS":
        df_keys = get_access_keys()
        db_countries = sorted(list(set(df_keys['country_label'].tolist())))
        country_list = ["CEETRIS", "GLOBAL"] + [c for c in db_countries if c not in ["CEETRIS", "GLOBAL"]]
        selected_country = st.sidebar.selectbox("Region:", country_list, index=0)
    else:
        selected_country = st.session_state.country
    selected_product = st.sidebar.selectbox("Product Portfolio:", ["Tecentriq", "Vabysmo", "Evrysdi"])
else:
    selected_country = st.session_state.country
    selected_product = st.session_state.product
    st.sidebar.title(f"📍 {selected_country}")

if st.sidebar.button("Logout"):
    st.session_state.auth = False
    st.rerun()

st.title(f"📊 {selected_country} - {selected_product}")

if st.session_state.role == "ADMIN":
    tabs = st.tabs(["📈 Analysis & Performance Breakdown"])
    tab_analysis = tabs[0]
else:
    tab_config, tab_actual, tab_analysis = st.tabs([
        "🎯 Targets (Config)", "📝 Actual Values", "📈 Analysis"
    ])

if st.session_state.role == "USER":
    with tab_config:
        st.subheader("Step 1: Metric Weights Configuration")
        df_config = get_kpi_config()
        df_config = df_config[
            (df_config['country_code'] == selected_country) &
            (df_config['product_name'] == selected_product)
        ].sort_values('id').reset_index(drop=True)
        if not df_config.empty:
            edited_c = st.data_editor(
                df_config, use_container_width=True, hide_index=True,
                key="ed_config_v1",
                column_config={
                    "id": None,
                    "country_code": None,
                    "product_name": None,
                    "category": st.column_config.TextColumn(disabled=True),
                    "metric": st.column_config.TextColumn(disabled=True)
                }
            )
            st.write("---")
            w_check = edited_c.groupby('category')['weight'].sum().reset_index()
            cols = st.columns(len(w_check))
            for i, row in w_check.iterrows():
                if 99.9 <= row['weight'] <= 100.1:
                    cols[i].success(f"✅ {row['category']}\n\n**{row['weight']}%**")
                else:
                    cols[i].error(f"⚠️ {row['category']}\n\n**{row['weight']}%**")
            if st.button("💾 Save Config"):
                with st.spinner("💾 Saving..."):
                    save_config(edited_c)
                    st.cache_data.clear()
                st.success("✅ Config Saved!")
                st.rerun()

if st.session_state.role == "USER":
    with tab_actual:
        st.subheader("Step 2: Monthly Actual Realizations")
        df_config = get_kpi_config()
        df_map = df_config[
            (df_config['country_code'] == selected_country) &
            (df_config['product_name'] == selected_product)
        ][['category', 'metric', 'weight']]
        active_metrics = df_map[df_map['weight'] > 0]['metric'].tolist()
        df_actuals = get_kpi_actuals()
        df_actuals = df_actuals[
            (df_actuals['country_code'] == selected_country) &
            (df_actuals['product_name'] == selected_product)
        ]
        if not df_actuals.empty:
            df_display = pd.merge(df_map[['category', 'metric']], df_actuals, on='metric')
            df_display = df_display[df_display['metric'].isin(active_metrics)]
            if df_display.empty:
                st.info("No active metrics. Set weights > 0 in Config tab.")
            else:
                edited_a = st.data_editor(
                    df_display, use_container_width=True, hide_index=True,
                    key="ed_actual_v1",
                    column_config={
                        "id": None,
                        "country_code": None,
                        "product_name": None,
                        "category": st.column_config.TextColumn(disabled=True),
                        "metric": st.column_config.TextColumn(disabled=True)
                    }
                )
                if st.button("💾 Save Actual Realizations"):
                    with st.spinner("📤 Uploading..."):
                        save_actuals(edited_a)
                        st.cache_data.clear()
                    st.success("✅ Actuals Saved!")
                    st.rerun()

with tab_analysis:
    if st.button("🚀 Run Analysis"):
        with st.spinner("🚀 Working on data insights..."):
            df_c = get_kpi_config()
            df_a = get_kpi_actuals()
            df_c = df_c[df_c['product_name'] == selected_product]
            df_a = df_a[df_a['product_name'] == selected_product]
            if not df_c.empty and not df_a.empty:
                df_c['metric'] = df_c['metric'].str.strip()
                df_a['metric'] = df_a['metric'].str.strip()
                all_cats = sorted(df_c['category'].unique())
                trend_results = []
                for m in months:
                    m_low = m.lower()
                    t_col = f"target_{m_low}"
                    a_col = f"act_{m_low}"
                    m_df = pd.merge(
                        df_c[['country_code', 'category', 'metric', 'weight', t_col]],
                        df_a[['metric', 'country_code', a_col]],
                        on=['metric', 'country_code']
                    )
                    m_df['score'] = (
                        m_df[a_col] / m_df[t_col].replace(0, float('nan'))
                    ).fillna(0).replace([float('inf')], 0) * (m_df['weight'] / 100)
                    if selected_country not in ["CEETRIS", "GLOBAL"]:
                        m_df = m_df[m_df['country_code'] == selected_country]
                    if selected_country in ["CEETRIS", "GLOBAL"]:
                        cat_summary = m_df.groupby('category')['score'].mean().to_dict()
                    else:
                        cat_summary = m_df.groupby('category')['score'].sum().to_dict()
                    for cat in all_cats:
                        if cat not in cat_summary:
                            cat_summary[cat] = 0
                    cat_summary['Month'] = m
                    trend_results.append(cat_summary)
                plot_df = pd.DataFrame(trend_results)
                fig = go.Figure()
                for cat in all_cats:
                    fig.add_trace(go.Scatter(
                        x=plot_df['Month'], y=plot_df[cat],
                        name=cat, mode='lines+markers'
                    ))
                fig.update_layout(
                    template="plotly_white", height=600,
                    yaxis=dict(tickformat=".0%", range=[0, 1.6]),
                    title=f"Strategic Performance Dashboard: {selected_product}"
                )
                st.plotly_chart(fig, use_container_width=True)
                if selected_country not in ["CEETRIS", "GLOBAL"]:
                    st.divider()
                    st.markdown(f"### 🔍 Detailed Audit: {selected_country}")
                    df_audit = df_c[df_c['country_code'] == selected_country]
                    for cat in all_cats:
                        met = df_audit[df_audit['category'] == cat]
                        total_w = met['weight'].sum()
                        active_count = len(met[met['weight'] > 0])
                        total_count = len(met)
                        icon = "🟢" if 99.9 <= total_w <= 100.1 else "🔴"
                        with st.expander(f"{icon} {cat} ({active_count}/{total_count} selected)"):
                            for _, r in met.iterrows():
                                if r['weight'] == 0:
                                    st.markdown(
                                        f"<span style='color:#ff4b4b;'>• {r['metric']}: **{r['weight']}% (DEACTIVATED)**</span>",
                                        unsafe_allow_html=True
                                    )
                                else:
                                    st.markdown(f"• {r['metric']}: **{r['weight']}%**")
