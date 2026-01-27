import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Coffee Sales Analytics")

st.title("☕ Аналітика продажів кави")

# Завантаження файлу
uploaded_file = st.file_uploader("Завантажте CSV файл", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Очистка даних: заміна порожніх значень на 0
    months = ['9.25', '10.25', '11.25', '12.25', '1.26']
    df[months] = df[months].fillna(0)

    # Функція для визначення статусу
    def get_status(row):
        jan = row['1.26']
        dec = row['12.25']
        if jan == 0 and dec == 0:
            return "🔴 Критична зона"
        if jan == 0:
            return "🟠 Термінова увага"
        if jan > dec:
            return "🟢 Ріст"
        return "🔵 В тренді"

    df['Статус'] = df.apply(get_status, axis=1)

    # --- ФІЛЬТРИ ---
    st.sidebar.header("Фільтри")
    manager = st.sidebar.multiselect("Менеджер", options=df['Менеджер'].unique(), default=df['Менеджер'].unique())
    status = st.sidebar.multiselect("Статус", options=df['Статус'].unique(), default=df['Статус'].unique())

    filtered_df = df[(df['Менеджер'].isin(manager)) & (df['Статус'].isin(status))]

    # --- ДАШБОРДИ ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Розподіл статусів")
        fig_pie = px.pie(filtered_df, names='Статус', color='Статус',
                         color_discrete_map={"🟢 Ріст":"green", "🔵 В тренді":"blue", 
                                             "🟠 Термінова увага":"orange", "🔴 Критична зона":"red"})
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("Продажі по менеджерам (січень)")
        fig_bar = px.bar(filtered_df, x='Менеджер', y='1.26', color='Статус', barmode='group')
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- ТАБЛИЦЯ ---
    st.subheader("Детальний аналіз клієнтів")
    
    # Кольорове оформлення таблиці
    def color_status(val):
        color = 'white'
        if "🔴" in val: color = '#ff4b4b'
        elif "🟠" in val: color = '#ffa500'
        elif "🟢" in val: color = '#28a745'
        return f'background-color: {color}; color: white; font-weight: bold'

    st.dataframe(filtered_df.style.applymap(color_status, subset=['Статус']), use_container_width=True)

    # Експорт результатів
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("Завантажити звіт у CSV", data=csv, file_name="sales_report.csv", mime="text/csv")
