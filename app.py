import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(layout="wide", page_title="Coffee Sales Analytics")

DEFAULT_FILE = "data_sales.csv"

st.title("☕ ОПТ: Аналітика продажів")

# --- ФУНКЦІЯ ВИЗНАЧЕННЯ КОЛОНОК-МІСЯЦІВ ---
def get_month_columns(df):
    # Шукаємо колонки, що відповідають паттерну цифри.цифри (напр. 9.25, 12.25, 01.26)
    pattern = re.compile(r'^\d{1,2}\.\d{2}$')
    month_cols = [col for col in df.columns if pattern.match(str(col))]
    
    # Сортуємо їх хронологічно
    # Перетворюємо в datetime для правильного сортування, потім повертаємо як назви
    def sort_key(col):
        m, y = map(int, col.split('.'))
        return y * 12 + m
    
    return sorted(month_cols, key=sort_key)

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
        
        # Визначаємо місяці динамічно
        actual_months = get_month_columns(df)
        
        if not actual_months:
            st.error("У файлі не знайдено колонок з датами у форматі 'М.РР' (напр. 9.25)")
            return None, []

        for m in actual_months:
            df[m] = pd.to_numeric(df[m].astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0)
        
        df['Менеджер'] = df['Менеджер'].fillna('Не вказано').astype(str).str.strip()
        df['Кліент'] = df['Кліент'].fillna('Невідомий').astype(str).str.strip()
        
        return df, actual_months
    except Exception as e:
        st.error(f"Помилка даних: {e}")
        return None, []

# --- СТАТУСИ ---
def get_status_label(row, months):
    if len(months) < 3:
        return "📊 Мало даних"
    
    vals = [row[m] for m in months]
    last, prev, pre_prev = vals[-1], vals[-2], vals[-3]
    
    # Новий: перші 60% періоду були нулі, а в кінці з'явилися продажі
    mid_point = len(vals) // 2
    if sum(vals[:mid_point]) == 0 and sum(vals[mid_point:]) > 0:
        return "✨ НОВИЙ"
    
    if last == 0 and prev > 0:
        return f"Відсутні в {months[-1]}"
    
    if last == 0 and prev == 0:
        return "🔴 ПРИПИНЕНО"
    
    if last > prev > pre_prev and pre_prev > 0:
        return "📈 РІСТ"
    
    if last < prev < pre_prev and last > 0:
        return "📉 ПАДІННЯ"
    
    # Перевірка на "дірки" (нулі між продажами)
    active_indices = [i for i, v in enumerate(vals) if v > 0]
    if len(active_indices) > 1:
        check_range = vals[min(active_indices):max(active_indices)]
        if 0 in check_range:
            return "🎲 НЕРЕГУЛЯРНО"
            
    return "✅ СТАБІЛЬНО"

# --- ОБРОБКА ---
uploaded_file = st.file_uploader("Завантажити файл", type="csv")
data_source = uploaded_file if uploaded_file else (DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else None)

if data_source:
    df, chrono_order = load_data(data_source)
    
    if df is not None:
        df['Аналітика'] = df.apply(lambda r: get_status_label(r, chrono_order), axis=1)
        
        cols_to_show = ['Менеджер', 'Кліент', 'Аналітика'] + chrono_order
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
            m_data = df_filtered.groupby('Менеджер')[chrono_order].sum().reset_index()
            m_melted = m_data.melt(id_vars=['Менеджер'], value_vars=chrono_order, var_name='Місяць', value_name='Сума')
            m_melted['Місяць'] = pd.Categorical(m_melted['Місяць'], categories=chrono_order, ordered=True)
            fig_mgr = px.line(m_melted.sort_values('Місяць'), x='Місяць', y='Сума', color='Менеджер', 
                              markers=True, title="Динаміка по менеджерам", template="plotly_white")
            st.plotly_chart(fig_mgr, use_container_width=True)

        with c2:
            sel_cl = st.multiselect("Виберіть клієнтів для аналізу", sorted(df_filtered['Кліент'].unique()))
            if sel_cl:
                cl_data = df_filtered[df_filtered['Кліент'].isin(sel_cl)]
                cl_melted = cl_data.melt(id_vars=['Кліент'], value_vars=chrono_order, var_name='Місяць', value_name='Сума')
                cl_melted['Місяць'] = pd.Categorical(cl_melted['Місяць'], categories=chrono_order, ordered=True)
                fig_cl = px.area(cl_melted.sort_values('Місяць'), x='Місяць', y='Сума', color='Кліент', 
                                 title="Об'єми закупівлі", template="plotly_white")
                st.plotly_chart(fig_cl, use_container_width=True)
            else:
                st.info("💡 Оберіть клієнтів для графіку")

        # --- ТАБЛИЦЯ ---
        st.subheader("📋 Детальний звіт")
        
        # Динамічно налаштовуємо назву останньої колонки для іконки
        last_month = chrono_order[-1]
        
        st.dataframe(
            df_filtered,
            column_config={
                "Аналітика": st.column_config.TextColumn("📊 Статус"),
                last_month: st.column_config.NumberColumn(f"Останній місяць ({last_month})", format="%.0f ☕"),
                "Кліент": st.column_config.TextColumn("Контрагент", width="large")
            },
            use_container_width=True,
            height=550,
            hide_index=True
        )

        csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Завантажити CSV", data=csv, file_name="sales_report.csv")
