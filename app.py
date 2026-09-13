import streamlit as st
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

                # Detailed Audit
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
