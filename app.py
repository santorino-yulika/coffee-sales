import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide", page_title="Coffee Sales Dashboard")

DEFAULT_FILE = "data_sales.csv"
# Важливо: задаємо чіткий порядок місяців для графіків
CHRONO_ORDER = ['9.25', '10.25', '11.25', '12.25', '1.26']

st.title("☕ Аналітична панель продажів")

@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file)
        df = df.dropna(subset=['Менеджер', 'Кліент'], how='all')
        df.columns = df.columns.str.strip()
        
        for m in CHRONO_ORDER:
            if m in df.columns:
                df[m] = pd.to_numeric(df[m], errors='coerce').fillna(0)
            else:
                df[m] = 0.0
        
        df['Менеджер'] = df['Менеджер'].fillna('Не вказано').astype(str).str.strip()
        df['Кліент'] = df['Кліент'].fillna('Невідомий клієнт').astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Помилка: {e}")
        return None

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
    if 0 in vals[next((i for i, x in enumerate(vals) if x > 0), 0):]:
        return "🎲 Нерегулярні продажі"
    return "✅ Стабільні продажі"

uploaded_file = st.file_uploader("Завантажити CSV", type="csv")
df_raw = load_data(uploaded_file if uploaded_file else DEFAULT_FILE)

if df_raw is not None:
    df = df_raw.copy()
    df['Статус'] = df.apply(get_detailed_status, axis=1)
    
    # Перевпорядкування колонок для зручності
    cols = ['Менеджер', 'Кліент', 'Статус'] + CHRONO_ORDER
    df = df[cols]

    # --- Фільтри ---
    st.sidebar.header("Налаштування")
    sel_managers = st.sidebar.multiselect("Менеджер", sorted(df['Менеджер'].unique()), default=df['Менеджер'].unique())
    df_filtered = df[df['Менеджер'].isin(sel_managers)]
    
    sel_clients = st.sidebar.multiselect("Клієнт", sorted(df_filtered['Кліент'].unique()))
    if sel_clients:
        df_filtered = df_filtered[df_filtered['Кліент'].isin(sel_clients)]

    # --- Графіки ---
    col1, col2 = st.columns(2)
    
    # Спільна функція для малювання ліній без "петель"
    def plot_trend(data, group_col, title):
        melted = data.melt(id_vars=[group_col], value_vars=CHRONO_ORDER, var_name='Місяць', value_name='Сума')
        # Фікс: перетворюємо Місяць у категорію з чітким порядком
        melted['Місяць'] = pd.Categorical(melted['Місяць'], categories=CHRONO_ORDER, ordered=True)
        melted = melted.sort_values([group_col, 'Місяць'])
        
        fig = px.line(melted, x='Місяць', y='Сума', color=group_col, markers=True, title=title,
                     color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_layout(xaxis_type='category') # Гарантує порядок на осі X
        return fig

    col1.plotly_chart(plot_trend(df_filtered.groupby('Менеджер')[CHRONO_ORDER].sum().reset_index(), 'Менеджер', "Тренди менеджерів"), use_container_width=True)
    
    if sel_clients:
        col2.plotly_chart(plot_trend(df_filtered, 'Кліент', "Тренди клієнтів"), use_container_width=True)
    else:
        col2.info("Виберіть клієнтів для порівняння")

    # --- Таблиця з підсвіткою ---
    st.subheader("📋 Детальний аналіз")
    
    def color_status(val):
        color = 'white'
        if "🚫" in str(val): color = '#ffcccc' # Червоний
        elif "⚠️" in str(val): color = '#fff2cc' # Жовтий
        elif "📈" in str(val): color = '#d9ead3' # Зелений
        elif "✨" in str(val): color = '#cfe2f3' # Блакитний
        return f'background-color: {color}'

    # Використовуємо Streamlit Column Config для красивих барів прямо в таблиці
    st.dataframe(
        df_filtered.style.applymap(color_status, subset=['Статус']),
        column_config={
            "1.26": st.column_config.ProgressColumn("Січень", format="%.0f", min_value=0, max_value=float(df[CHRONO_ORDER].max().max())),
            "Статус": st.column_config.TextColumn("Аналітика", width="large")
        },
        use_container_width=True,
        height=600
    )
