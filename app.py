import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(layout="wide", page_title="Coffee Sales Analytics")

# Шлях до файлу за замовчуванням
DEFAULT_FILE = "data_sales.csv"
MONTHS_COLS = ['9.25', '10.25', '11.25', '12.25', '1.26']

st.title("☕ Аналітика активності клієнтської бази")

# --- ФУНКЦІЯ ЗАВАНТАЖЕННЯ ДАНИХ ---
@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file)
        
        # Видаляємо повністю порожні рядки
        df = df.dropna(subset=['Менеджер', 'Кліент'], how='all')
        
        # Очищуємо назви колонок від пробілів
        df.columns = df.columns.str.strip()
        
        # Перетворюємо числові колонки та обробляємо NaN
        for m in MONTHS_COLS:
            if m in df.columns:
                df[m] = pd.to_numeric(df[m], errors='coerce').fillna(0)
            else:
                df[m] = 0.0
        
        # Очищуємо текстові колонки від NaN, щоб уникнути помилок сортування
        df['Менеджер'] = df['Менеджер'].fillna('Не вказано').astype(str).str.strip()
        df['Кліент'] = df['Кліент'].fillna('Невідомий клієнт').astype(str).str.strip()
        
        return df
    except Exception as e:
        st.error(f"❌ Помилка при читанні файлу: {e}")
        return None

# --- ЛОГІКА ВИЗНАЧЕННЯ СТАТУСУ ---
def get_detailed_status(row):
    vals = [row[m] for m in MONTHS_COLS]
    jan, dec, nov = vals[-1], vals[-2], vals[-3]
    
    # 1. Новий клієнт
    if sum(vals[:3]) == 0 and sum(vals[3:]) > 0:
        return "✨ новий клієнт"
    
    # 2. Відсутність продажів в останній місяць
    if jan == 0 and dec > 0:
        return "⚠️ відсутні продажі в останній звітний місяць"
    
    # 3. Припинення відвантажень
    if jan == 0 and dec == 0:
        last_month = "давно"
        for i in range(len(MONTHS_COLS)-1, -1, -1):
            if vals[i] > 0:
                last_month = MONTHS_COLS[i]
                break
        return f"🚫 припинення відвантажень з {last_month}"

    # 4. Ріст
    if jan > dec > nov and nov > 0:
        return "📈 ріст"
        
    # 5. Стабільне падіння
    if jan < dec < nov and jan > 0:
        return "📉 стабільне падіння продажів"
    
    # 6. Нерегулярні продажі
    active_indices = [i for i, v in enumerate(vals) if v > 0]
    if len(active_indices) > 1:
        check_range = vals[min(active_indices):max(active_indices)]
        if 0 in check_range:
            return "🎲 нерегулярні продажі"
    
    return "✅ стабільні продажі"

# --- ОСНОВНИЙ БЛОК ЗАВАНТАЖЕННЯ ---
uploaded_file = st.file_uploader("Оновити базу (завантажити новий CSV)", type="csv")

df_raw = None
if uploaded_file is not None:
    df_raw = load_data(uploaded_file)
elif os.path.exists(DEFAULT_FILE):
    df_raw = load_data(DEFAULT_FILE)
else:
    st.info("👋 Завантажте файл `data_sales.csv` або додайте його в репозиторій GitHub.")

# --- ВІДОБРАЖЕННЯ ІНТЕРФЕЙСУ ---
if df_raw is not None:
    df = df_raw.copy()
    
    # Додаємо статуси та міняємо порядок колонок
    df['Статус'] = df.apply(get_detailed_status, axis=1)
    cols = list(df.columns)
    client_idx = cols.index('Кліент')
    cols.insert(client_idx + 1, cols.pop(cols.index('Статус')))
    df = df[cols]

    # --- СТРУКТУРА ФІЛЬТРІВ ---
    st.sidebar.header("🔍 Налаштування")
    
    all_managers = sorted(df['Менеджер'].unique())
    selected_managers = st.sidebar.multiselect("Менеджер", options=all_managers, default=all_managers)
    
    filtered_by_manager = df[df['Менеджер'].isin(selected_managers)]
    all_clients = sorted(filtered_by_manager['Кліент'].unique())
    selected_clients = st.sidebar.multiselect("Клієнт (пошук)", options=all_clients)

    # Остаточна фільтрація
    display_df = filtered_by_manager.copy()
    if selected_clients:
        display_df = display_df[display_df['Кліент'].isin(selected_clients)]

    # --- ДАШБОРДИ ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Тренди менеджерів")
        m_trend = display_df.groupby('Менеджер')[MONTHS_COLS].sum().reset_index()
        m_melted = m_trend.melt(id_vars='Менеджер', var_name='Місяць', value_name='Сума')
        fig_m = px.line(m_melted, x='Місяць', y='Сума', color='Менеджер', markers=True)
        st.plotly_chart(fig_m, use_container_width=True)

    with col2:
        st.subheader("👤 Динаміка вибраних клієнтів")
        if not selected_clients:
            st.info("Виберіть клієнтів у фільтрі для порівняння")
        else:
            c_melted = display_df.melt(id_vars='Кліент', value_vars=MONTHS_COLS, var_name='Місяць', value_name='Сума')
            fig_c = px.line(c_melted, x='Місяць', y='Сума', color='Кліент', markers=True)
            st.plotly_chart(fig_c, use_container_width=True)

    # --- ТАБЛИЦЯ ---
    st.subheader("📋 Детальний аналіз бази")

    def style_rows(row):
        status = row['Статус']
        color = ''
        if "⚠️" in status: color = 'background-color: #fff4e6' # помаранчевий
        elif "🚫" in status: color = 'background-color: #ffeef0' # червоний
        elif "📈" in status: color = 'background-color: #f0fff4' # зелений
        return [color] * len(row)

    st.dataframe(display_df.style.apply(style_rows, axis=1), use_container_width=True, height=500)

    # Експорт
    csv = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Завантажити цей звіт у CSV", data=csv, file_name="sales_report.csv")
