import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(layout="wide", page_title="Coffee Sales Dashboard")

DEFAULT_FILE = "data_sales.csv"
CHRONO_ORDER = ['9.25', '10.25', '11.25', '12.25', '1.26']

st.title("☕ Аналітика продажів та активності")

# --- ФУНКЦІЯ ЗАВАНТАЖЕННЯ ---
@st.cache_data
def load_data(file_source):
    try:
        # Автовизначення кодування (UTF-8 або Windows-1251)
        try:
            df = pd.read_csv(file_source, encoding='utf-8')
        except:
            df = pd.read_csv(file_source, encoding='windows-1251', sep=None, engine='python')
            
        df = df.dropna(subset=['Менеджер', 'Кліент'], how='all')
        df.columns = df.columns.str.strip()
        
        # Перетворення числових колонок (заміна коми на крапку)
        for m in CHRONO_ORDER:
            if m in df.columns:
                df[m] = pd.to_numeric(df[m].astype(str).str.replace(',', '.').replace('nan', '0'), errors='coerce').fillna(0)
            else:
                df[m] = 0.0
        
        df['Менеджер'] = df['Менеджер'].fillna('Не вказано').astype(str).str.strip()
        df['Кліент'] = df['Кліент'].fillna('Невідомий клієнт').astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Помилка завантаження файлу: {e}")
        return None

# --- ЛОГІКА СТАТУСІВ ---
def get_detailed_status(row):
    vals = [row[m] for m in CHRONO_ORDER]
    jan, dec, nov = vals[-1], vals[-2], vals[-3]
    
    if sum(vals[:3]) == 0 and sum(vals[3:]) > 0:
        return "✨ Новий клієнт"
    if jan == 0 and dec > 0:
        return "⚠️ Відсутні (січень 0)"
    if jan == 0 and dec == 0:
        last_m = "давно"
        for i in range(len(CHRONO_ORDER)-1, -1, -1):
            if vals[i] > 0:
                last_m = CHRONO_ORDER[i]
                break
        return f"🚫 Немає відвантажень з {last_m}"
    if jan > dec > nov and nov > 0:
        return "📈 Ріст"
    if jan < dec < nov and jan > 0:
        return "📉 Стабільне падіння"
    
    active = [i for i, v in enumerate(vals) if v > 0]
    if len(active) > 1 and 0 in vals[min(active):max(active)]:
        return "🎲 Нерегулярні продажі"
        
    return "✅ Стабільні продажі"

# --- ОБРОБКА ДАНИХ ---
uploaded_file = st.file_uploader("Завантажте свій CSV", type="csv")
data_source = uploaded_file if uploaded_file else (DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else None)

if data_source:
    df = load_data(data_source)
    if df is not None:
        df['Статус'] = df.apply(get_detailed_status, axis=1)
        
        # Колонки для відображення
        display_cols = ['Менеджер', 'Кліент', 'Статус'] + CHRONO_ORDER
        df_display = df[display_cols]

        # --- ФІЛЬТРИ ---
        st.sidebar.header("Налаштування")
        all_mgr = sorted(df_display['Менеджер'].unique())
        sel_mgr = st.sidebar.multiselect("Менеджер", all_mgr, default=all_mgr)
        
        all_st = sorted(df_display['Статус'].unique())
        sel_status = st.sidebar.multiselect("Статус", all_st, default=all_st)
        
        final_df = df_display[(df_display['Менеджер'].isin(sel_mgr)) & (df_display['Статус'].isin(sel_status))]

        # --- ГРАФІКИ (БЕЗ ПЕТЕЛЬ) ---
        col1, col2 = st.columns(2)
        
        def draw_line_chart(data, group_col, title):
            melted = data.melt(id_vars=[group_col], value_vars=CHRONO_ORDER, var_name='Місяць', value_name='Продажі')
            melted['Місяць'] = pd.Categorical(melted['Місяць'], categories=CHRONO_ORDER, ordered=True)
            melted = melted.sort_values('Місяць')
            fig = px.line(melted, x='Місяць', y='Продажі', color=group_col, markers=True, title=title)
            fig.update_layout(xaxis_type='category')
            return fig

        col1.plotly_chart(draw_line_chart(final_df.groupby('Менеджер')[CHRONO_ORDER].sum().reset_index(), 'Менеджер', "Тренди Менеджерів"), use_container_width=True)
        
        sel_cl = st.sidebar.multiselect("Оберіть клієнтів для порівняння", sorted(final_df['Кліент'].unique()))
        if sel_cl:
            col2.plotly_chart(draw_line_chart(final_df[final_df['Кліент'].isin(sel_cl)], 'Кліент', "Тренди Клієнтів"), use_container_width=True)
        else:
            col2.info("Оберіть клієнтів у списку зліва для графіку")

        # --- ТАБЛИЦЯ ---
        st.subheader("📋 Детальна таблиця аналізу")
        
        # Функція для підсвітки рядків (весь рядок фарбується залежно від статусу)
        def style_rows(row):
            status = row['Статус']
            if "🚫" in status: color = '#f8d7da' # Світло-червоний
            elif "⚠️" in status: color = '#fff3cd' # Світло-жовтий
            elif "📉" in status: color = '#f5eef8' # Лавандовий (падіння)
            elif "📈" in status or "✨" in status: color = '#d4edda' # Світло-зелений
            else: color = 'white'
            return [f'background-color: {color}'] * len(row)

        st.dataframe(
            final_df.style.apply(style_rows, axis=1),
            use_container_width=True,
            height=600
        )
else:
    st.warning("⚠️ Файл не знайдено. Завантажте CSV-файл.")
