import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(layout="wide", page_title="Sales Report Pro")

DEFAULT_FILE = "data_sales.csv"
CHRONO_ORDER = ['9.25', '10.25', '11.25', '12.25', '1.26']

st.title("☕ Аналітика продажів кави")

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
                # Чистимо числа: прибираємо пробіли, міняємо коми на крапки
                df[m] = pd.to_numeric(df[m].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0)
            else:
                df[m] = 0.0
        
        df['Менеджер'] = df['Менеджер'].fillna('Не вказано').astype(str).str.strip()
        df['Кліент'] = df['Кліент'].fillna('Невідомий').astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Помилка даних: {e}")
        return None

# --- СТАТУСИ З ЕМОДЗІ ---
def get_status_label(row):
    vals = [row[m] for m in CHRONO_ORDER]
    jan, dec, nov = vals[-1], vals[-2], vals[-3]
    
    if sum(vals[:3]) == 0 and sum(vals[3:]) > 0:
        return "✨ НОВИЙ"
    if jan == 0 and dec > 0:
        return "ВІДСУТНІ в останному місяці"
    if jan == 0 and dec == 0:
        return "🔴 ПРИПИНЕНО"
    if jan > dec > nov and nov > 0:
        return "📈 РІСТ"
    if jan < dec < nov and jan > 0:
        return "📉 ПАДІННЯ"
    if 0 in vals[next((i for i, x in enumerate(vals) if x > 0), 0):]:
        return "🎲 НЕРЕГУЛЯРНО"
    return "✅ СТАБІЛЬНО"

# --- ЛОГІКА ---
uploaded_file = st.file_uploader("Завантажити новий файл", type="csv")
data_source = uploaded_file if uploaded_file else (DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else None)

if data_source:
    df = load_data(data_source)
    if df is not None:
        df['Аналітика'] = df.apply(get_status_label, axis=1)
        
        # Вибираємо та впорядковуємо колонки
        cols_to_show = ['Менеджер', 'Кліент', 'Аналітика', '1.26', '12.25', '11.25', '10.25', '9.25']
        df_final = df[cols_to_show].copy()

        # Фільтри
        st.sidebar.header("Налаштування")
        sel_mgr = st.sidebar.multiselect("Менеджер", sorted(df_final['Менеджер'].unique()), default=df_final['Менеджер'].unique())
        sel_st = st.sidebar.multiselect("Статус", sorted(df_final['Аналітика'].unique()), default=df_final['Аналітика'].unique())
        
        df_filtered = df_final[(df_final['Менеджер'].isin(sel_mgr)) & (df_final['Аналітика'].isin(sel_st))]

        # --- ГРАФІКИ ---
        st.subheader("📊 Динаміка")
        def draw_chart(data, color_col, title):
            m = data.melt(id_vars=[color_col], value_vars=CHRONO_ORDER, var_name='Місяць', value_name='Продажі')
            m['Місяць'] = pd.Categorical(m['Місяць'], categories=CHRONO_ORDER, ordered=True)
            fig = px.line(m.sort_values('Місяць'), x='Місяць', y='Продажі', color=color_col, markers=True, title=title)
            fig.update_layout(xaxis_type='category')
            return fig

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(draw_chart(df_filtered.groupby('Менеджер')[CHRONO_ORDER].sum().reset_index(), 'Менеджер', "По менеджерам"), use_container_width=True)
        with c2:
            sel_cl = st.multiselect("Виберіть клієнтів для порівняння", sorted(df_filtered['Кліент'].unique()))
            if sel_cl:
                st.plotly_chart(draw_chart(df_filtered[df_filtered['Кліент'].isin(sel_cl)], 'Кліент', "По клієнтам"), use_container_width=True)

        # --- ТАБЛИЦЯ (БЕЗ ФОНОВОЇ ЗАЛИВКИ) ---
        st.subheader("📋 Детальний звіт")
        
        # Форматуємо таблицю: Січень виділяємо кольором тексту, а не фоном
        st.dataframe(
            df_filtered,
            column_config={
                "1.26": st.column_config.NumberColumn("СІЧЕНЬ", format="%.2f", help="Продажі за останній місяць"),
                "Аналітика": st.column_config.TextColumn("СТАТУС", width="medium"),
                "Кліент": st.column_config.TextColumn("КЛІЄНТ", width="large"),
            },
            use_container_width=True,
            height=600,
            hide_index=True
        )
else:
    st.info("Чекаю на файл...")
