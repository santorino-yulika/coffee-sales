import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(layout="wide", page_title="Coffee Sales Analytics")

DEFAULT_FILE = "data_sales.csv"
CHRONO_ORDER = ['9.25', '10.25', '11.25', '12.25', '1.26']

st.title("☕ ОПТ: Аналітика продажів")

# --- ЗАВАНТАЖЕННЯ ---
@st.cache_data
def load_data(file_source):
    try:
        try:
            df = pd.read_csv(file_source, encoding='utf-8')
        except:
            df = pd.read_csv(file_source, encoding='windows-1251', sep=None, engine='python')
            
        df = df.dropna(subset=['Менеджер', 'Кліент'], how='all')
        df.columns = df.columns.str.strip()
        
        for m in CHRONO_ORDER:
            if m in df.columns:
                df[m] = pd.to_numeric(df[m].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0)
            else:
                df[m] = 0.0
        
        df['Менеджер'] = df['Менеджер'].fillna('Не вказано').astype(str).str.strip()
        df['Кліент'] = df['Кліент'].fillna('Невідомий').astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Помилка даних: {e}")
        return None

# --- СТАТУСИ ---
def get_status_label(row):
    vals = [row[m] for m in CHRONO_ORDER]
    jan, dec, nov = vals[-1], vals[-2], vals[-3]
    
    if sum(vals[:3]) == 0 and sum(vals[3:]) > 0:
        return "✨ НОВИЙ"
    if jan == 0 and dec > 0:
        return "ВІДСУТНІ в січні"
    if jan == 0 and dec == 0:
        return "🔴 ПРИПИНЕНО"
    if jan > dec > nov and nov > 0:
        return "📈 РІСТ"
    if jan < dec < nov and jan > 0:
        return "📉 ПАДІННЯ"
    if 0 in vals[next((i for i, x in enumerate(vals) if x > 0), 0):]:
        return "🎲 НЕРЕГУЛЯРНО"
    return "✅ СТАБІЛЬНО"

# --- ОБРОБКА ---
uploaded_file = st.file_uploader("Завантажити файл", type="csv")
data_source = uploaded_file if uploaded_file else (DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else None)

if data_source:
    df = load_data(data_source)
    if df is not None:
        df['Аналітика'] = df.apply(get_status_label, axis=1)
        
        # Порядок колонок як у вхідному файлі: Менеджер, Клієнт, Статус, потім місяці 09->01
        cols_to_show = ['Менеджер', 'Кліент', 'Аналітика'] + CHRONO_ORDER
        df_final = df[cols_to_show].copy()

        # Фільтри
        st.sidebar.header("Налаштування")
        sel_mgr = st.sidebar.multiselect("Менеджер", sorted(df_final['Менеджер'].unique()), default=df_final['Менеджер'].unique())
        sel_st = st.sidebar.multiselect("Статус", sorted(df_final['Аналітика'].unique()), default=df_final['Аналітика'].unique())
        
        df_filtered = df_final[(df_final['Менеджер'].isin(sel_mgr)) & (df_final['Аналітика'].isin(sel_st))]

        # --- ДАШБОРДИ ---
        st.subheader("📊 Візуалізація трендів")
        
        c1, c2 = st.columns(2)
        
        with c1:
            # Тренди менеджерів - залишаємо лінійний для чіткості
            m_data = df_filtered.groupby('Менеджер')[CHRONO_ORDER].sum().reset_index()
            m_melted = m_data.melt(id_vars=['Менеджер'], value_vars=CHRONO_ORDER, var_name='Місяць', value_name='Сума')
            m_melted['Місяць'] = pd.Categorical(m_melted['Місяць'], categories=CHRONO_ORDER, ordered=True)
            fig_mgr = px.line(m_melted.sort_values('Місяць'), x='Місяць', y='Сума', color='Менеджер', 
                              markers=True, title="Динаміка по менеджерам", template="plotly_white")
            st.plotly_chart(fig_mgr, use_container_width=True)

        with c2:
            # Тренди клієнтів - робимо Area Chart (Графік з областями)
            sel_cl = st.multiselect("Виберіть клієнтів для аналізу", sorted(df_filtered['Кліент'].unique()))
            if sel_cl:
                cl_data = df_filtered[df_filtered['Кліент'].isin(sel_cl)]
                cl_melted = cl_data.melt(id_vars=['Кліент'], value_vars=CHRONO_ORDER, var_name='Місяць', value_name='Сума')
                cl_melted['Місяць'] = pd.Categorical(cl_melted['Місяць'], categories=CHRONO_ORDER, ordered=True)
                # Area chart виглядає значно краще для порівняння об'ємів
                fig_cl = px.area(cl_melted.sort_values('Місяць'), x='Місяць', y='Сума', color='Кліент', 
                                 title="Об'єми закупівлі вибраних клієнтів", template="plotly_white",
                                 line_group='Кліент')
                st.plotly_chart(fig_cl, use_container_width=True)
            else:
                st.info("💡 Оберіть декілька клієнтів вище, щоб побачити їх порівняльну динаміку")

        # --- ТАБЛИЦЯ ---
        st.subheader("📋 Детальний звіт")
        
        st.dataframe(
            df_filtered,
            column_config={
                "Аналітика": st.column_config.TextColumn("📊 Статус", width="medium"),
                "1.26": st.column_config.NumberColumn("Січень", format="%.0f ☕"),
                "Кліент": st.column_config.TextColumn("Контрагент", width="large")
            },
            use_container_width=True,
            height=550,
            hide_index=True
        )

        # Кнопка експорту
        csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Завантажити звіт у CSV", data=csv, file_name="coffee_report.csv")
else:
    st.info("Потрібен файл data_sales.csv для відображення")
