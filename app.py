import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(layout="wide", page_title="Coffee Sales Analytics")

DEFAULT_FILE = "data_sales.csv"
# Чітка послідовність місяців для осі X
CHRONO_ORDER = ['9.25', '10.25', '11.25', '12.25', '1.26']

st.title("☕ Аналітична панель продажів")

# --- ФУНКЦІЯ ЗАВАНТАЖЕННЯ ---
@st.cache_data
def load_data(file_source):
    try:
        # Спробуємо прочитати з різними кодуваннями
        try:
            df = pd.read_csv(file_source, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_source, encoding='windows-1251', sep=None, engine='python')
            
        # Очистка структури
        df = df.dropna(subset=['Менеджер', 'Кліент'], how='all')
        df.columns = df.columns.str.strip()
        
        # Перетворення числових даних
        for m in CHRONO_ORDER:
            if m in df.columns:
                df[m] = pd.to_numeric(df[m].astype(str).str.replace(',', '.').replace('nan', '0'), errors='coerce').fillna(0)
            else:
                df[m] = 0.0
        
        df['Менеджер'] = df['Менеджер'].fillna('Не вказано').astype(str).str.strip()
        df['Кліент'] = df['Кліент'].fillna('Невідомий клієнт').astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Помилка завантаження: {e}")
        return None

# --- ЛОГІКА СТАТУСІВ ---
def get_detailed_status(row):
    vals = [row[m] for m in CHRONO_ORDER]
    jan, dec, nov = vals[-1], vals[-2], vals[-3]
    
    if sum(vals[:3]) == 0 and sum(vals[3:]) > 0:
        return "✨ Новий клієнт"
    if jan == 0 and dec > 0:
        return "⚠️ Відсутні в останній місяць"
    if jan == 0 and dec == 0:
        last_m = "давно"
        for i in range(len(CHRONO_ORDER)-1, -1, -1):
            if vals[i] > 0:
                last_m = CHRONO_ORDER[i]
                break
        return f"🚫 Припинення з {last_m}"
    if jan > dec > nov and nov > 0:
        return "📈 Ріст"
    if jan < dec < nov and jan > 0:
        return "📉 Стабільне падіння"
    
    # Нерегулярність (перевірка на дірки між замовленнями)
    active = [i for i, v in enumerate(vals) if v > 0]
    if len(active) > 1 and 0 in vals[min(active):max(active)]:
        return "🎲 Нерегулярні продажі"
        
    return "✅ Стабільні продажі"

# --- ОБРОБКА ДАНИХ ---
uploaded_file = st.file_uploader("Завантажте свій CSV", type="csv")
data_source = uploaded_file if uploaded_file else (DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else None)

if data_source:
    df_raw = load_data(data_source)
    if df_raw is not None:
        df = df_raw.copy()
        df['Статус'] = df.apply(get_detailed_status, axis=1)
        
        # Формуємо порядок колонок
        display_cols = ['Менеджер', 'Кліент', 'Статус'] + CHRONO_ORDER
        df = df[display_cols]

        # --- БІЧНА ПАНЕЛЬ ---
        st.sidebar.header("Фільтри")
        all_st = sorted(df['Статус'].unique())
        sel_status = st.sidebar.multiselect("Статус", all_st, default=all_st)
        
        all_mgr = sorted(df['Менеджер'].unique())
        sel_mgr = st.sidebar.multiselect("Менеджер", all_mgr, default=all_mgr)
        
        df_filtered = df[(df['Статус'].isin(sel_status)) & (df['Менеджер'].isin(sel_mgr))]
        
        all_cl = sorted(df_filtered['Кліент'].unique())
        sel_cl = st.sidebar.multiselect("Клієнт (для тренду)", all_cl)

        # --- ГРАФІКИ ---
        col1, col2 = st.columns(2)

        def make_plot(data, group_col, title):
            melted = data.melt(id_vars=[group_col], value_vars=CHRONO_ORDER, var_name='Місяць', value_name='Сума')
            melted['Місяць'] = pd.Categorical(melted['Місяць'], categories=CHRONO_ORDER, ordered=True)
            melted = melted.sort_values('Місяць')
            fig = px.line(melted, x='Місяць', y='Сума', color=group_col, markers=True, title=title)
            fig.update_layout(xaxis_type='category')
            return fig

        with col1:
            mgr_data = df_filtered.groupby('Менеджер')[CHRONO_ORDER].sum().reset_index()
            st.plotly_chart(make_plot(mgr_data, 'Менеджер', "Тренди Менеджерів"), use_container_width=True)

        with col2:
            if sel_cl:
                cl_data = df_filtered[df_filtered['Кліент'].isin(sel_cl)]
                st.plotly_chart(make_plot(cl_data, 'Кліент', "Тренди Клієнтів"), use_container_width=True)
            else:
                st.info("Оберіть клієнтів у фільтрі для відображення графіку")

        # --- ТАБЛИЦЯ ---
        st.subheader("📋 Детальна аналітика")

        def color_status(val):
            bg = 'white'
            if "🚫" in val: bg = '#ffdbdb'
            elif "⚠️" in val: bg = '#fff4cc'
            elif "📈" in val: bg = '#e2fce2'
            elif "📉" in val: bg = '#fde2ff'
            return f'background-color: {bg}'

        st.dataframe(
            df_filtered.style.applymap(color_status, subset=['Статус']),
            column_config={
                "1.26": st.column_config.ProgressColumn("Січень", format="%.0f", min_value=0, max_value=float(df[CHRONO_ORDER].max().max())),
                "Статус": st.column_config.TextColumn("Статус", width="medium")
            },
            use_container_width=True,
            height=600
        )
else:
    st.warning("⚠️ Файл не знайдено. Будь ласка, завантажте CSV або переконайтеся, що `data_sales.csv` є в папці проекту.")
