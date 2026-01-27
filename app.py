import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide", page_title="Coffee Sales Dashboard")

# Шлях до файлу за замовчуванням на GitHub
DEFAULT_FILE = "data_sales.csv"

st.title("☕ Моніторинг активності клієнтів")

# Логіка завантаження: або завантажений файл, або файл за замовчуванням
uploaded_file = st.file_uploader("Оновити дані (завантажити новий CSV)", type="csv")

@st.cache_data
def load_data(file):
    # Читаємо файл
    df = pd.read_csv(file)
    
    # 1. Видаляємо рядки, де немає ні менеджера, ні клієнта (порожні рядки в кінці файлу)
    df = df.dropna(subset=['Менеджер', 'Кліент'], how='all')
    
    # 2. Очищуємо назви колонок (про всяк випадок)
    df.columns = df.columns.str.strip()
    
    months = ['9.25', '10.25', '11.25', '12.25', '1.26']
    
    # 3. Заповнюємо пусті значення в числових колонках
    for m in months:
        if m in df.columns:
            df[m] = pd.to_numeric(df[m], errors='coerce').fillna(0)
    
    # 4. ОБОВ'ЯЗКОВО: Перетворюємо менеджерів та клієнтів у текст і заповнюємо пустоти
    df['Менеджер'] = df['Менеджер'].fillna('Не вказано').astype(str).str.strip()
    df['Кліент'] = df['Кліент'].fillna('Невідомий клієнт').astype(str).str.strip()
    
    return df, months

# ... далі в основному коді, де фільтри:

if df_raw is not None:
    df = df_raw.copy()
    
    # (тут залишається ваша логіка статусів)
    # ... 

    # --- БЛОК ФІЛЬТРІВ (Виправлений) ---
    st.sidebar.header("🔍 Фільтрація")
    
    # Використовуємо список унікальних значень, які вже гарантовано є рядками
    all_managers = sorted(df['Менеджер'].unique())
    selected_managers = st.sidebar.multiselect("Виберіть менеджера", options=all_managers, default=all_managers)
    
    # Динамічний фільтр клієнтів
    filtered_by_manager = df[df['Менеджер'].isin(selected_managers)]
    all_clients = sorted(filtered_by_manager['Кліент'].unique())
    selected_clients = st.sidebar.multiselect("Пошук по клієнту", options=all_clients)

# Перевірка наявності даних
df_raw = None
if uploaded_file is not None:
    df_raw, months_cols = load_data(uploaded_file)
elif os.path.exists(DEFAULT_FILE):
    df_raw, months_cols = load_data(DEFAULT_FILE)
else:
    st.error(f"Файл {DEFAULT_FILE} не знайдено в репозиторії. Будь ласка, завантажте файл вручну.")

if df_raw is not None:
    df = df_raw.copy()

    # --- УДОСКОНАЛЕНА ЛОГІКА СТАТУСІВ ---
    def get_detailed_status(row):
        vals = [row[m] for m in months_cols]
        jan, dec, nov = vals[-1], vals[-2], vals[-3]
        
        # 1. Новий клієнт (не було продажів у перші 3 місяці)
        if sum(vals[:3]) == 0 and sum(vals[3:]) > 0:
            return "✨ новий клієнт"
        
        # 2. Відсутність продажів в останній місяць
        if jan == 0 and dec > 0:
            return "⚠️ відсутні продажі в останній звітний місяць"
        
        # 3. Припинення відвантажень (нулі в останні 2+ місяці)
        if jan == 0 and dec == 0:
            last_active_month = "невідомо"
            for i in range(len(months_cols)-1, -1, -1):
                if vals[i] > 0:
                    last_active_month = months_cols[i]
                    break
            return f"🚫 припинення відвантажень з {last_active_month}"

        # 4. Ріст
        if jan > dec > nov and nov > 0:
            return "📈 ріст"
            
        # 5. Стабільне падіння
        if jan < dec < nov and jan > 0:
            return "📉 стабільне падіння продажів"
        
        # 6. Нерегулярні продажі (наявність нулів між закупівлями)
        active_vals = [v for v in vals if v > 0]
        if 0 in vals and len(active_vals) > 1:
            # Перевіряємо, чи був нуль між ненульовими значеннями
            first_idx = next(i for i, v in enumerate(vals) if v > 0)
            last_idx = max(i for i, v in enumerate(vals) if v > 0)
            if 0 in vals[first_idx:last_idx]:
                return "🎲 нерегулярні продажі"
        
        return "✅ стабільні продажі"

    df['Статус'] = df.apply(get_detailed_status, axis=1)

    # Перевпорядкування колонок: Статус після Клієнта
    cols = list(df.columns)
    client_idx = cols.index('Кліент')
    cols.insert(client_idx + 1, cols.pop(cols.index('Статус')))
    df = df[cols]

    # --- БЛОК ФІЛЬТРІВ ---
    st.sidebar.header("🔍 Фільтрація")
    
    all_managers = sorted(df['Менеджер'].unique())
    selected_managers = st.sidebar.multiselect("Виберіть менеджера", options=all_managers, default=all_managers)
    
    # Динамічний фільтр клієнтів
    filtered_by_manager = df[df['Менеджер'].isin(selected_managers)]
    all_clients = sorted(filtered_by_manager['Кліент'].unique())
    selected_clients = st.sidebar.multiselect("Пошук по клієнту", options=all_clients)

    # Фінальний датафрейм для відображення
    display_df = filtered_by_manager.copy()
    if selected_clients:
        display_df = display_df[display_df['Кліент'].isin(selected_clients)]

    # --- ВІЗУАЛІЗАЦІЯ (ДАНІ) ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Тренди по менеджерам")
        m_trend = display_df.groupby('Менеджер')[months_cols].sum().reset_index()
        m_melted = m_trend.melt(id_vars='Менеджер', var_name='Місяць', value_name='Сума')
        fig_m = px.line(m_melted, x='Місяць', y='Сума', color='Менеджер', markers=True, template="plotly_white")
        st.plotly_chart(fig_m, use_container_width=True)

    with col2:
        st.subheader("👤 Тренди вибраних клієнтів")
        if not selected_clients:
            st.info("Виберіть клієнтів у фільтрі, щоб побачити графік динаміки")
        else:
            c_melted = display_df.melt(id_vars='Кліент', value_vars=months_cols, var_name='Місяць', value_name='Сума')
            fig_c = px.line(c_melted, x='Місяць', y='Сума', color='Кліент', markers=True, template="plotly_white")
            st.plotly_chart(fig_c, use_container_width=True)

    # --- ТАБЛИЦЯ ---
    st.subheader("📋 Детальний звіт")

    def style_status(val):
        if "відсутні" in val or "падіння" in val: color = "#fff2f2" # Слабкий червоний
        elif "припинення" in val: color = "#ffe5e5" # Насичений червоний
        elif "ріст" in val or "новий" in val: color = "#f2fff2" # Зелений
        elif "нерегулярні" in val: color = "#fff9e6" # Жовтий
        else: color = "white"
        return f'background-color: {color}'

    st.dataframe(display_df.style.applymap(style_status, subset=['Статус']), use_container_width=True, height=600)

    # Кнопка експорту
    csv = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("💾 Завантажити відфільтровані дані", data=csv, file_name="sales_export.csv", mime="text/csv")
