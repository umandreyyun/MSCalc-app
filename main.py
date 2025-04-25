import streamlit as st
import plotly.express as px
import pandas as pd
import openpyxl
import io
import os
from pathlib import Path
import matplotlib.pyplot as plt
from fpdf import FPDF
import base64
from datetime import datetime

import re

# Настройки страницы
st.set_page_config(
    page_title="Калькулятор ремонта гидроцилиндров",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Функция для загрузки данных по умолчанию
def load_default_data():
    return pd.DataFrame({
        "MaterialName": [
            "Труба E355 40x50",
            "Шток 42CrMo4 Ø20",
            "Кругляк 45 Ø40",
            "Кругляк 45 Ø50",
            "Кругляк 45 Ø60",
            "Кругляк 45 Ø70",
            "Кругляк 45 Ø80",
            "Кругляк 45 Ø90",
            "Кругляк 45 Ø100"
        ],
        "Cost": [5400.0, 9200.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0, 4500.0, 5000.0],
        "Units": ["м", "м", "м", "м", "м", "м", "м", "м", "м"],
        "LastUpdated": [datetime.now().date()] * 9
    })


# Инициализация данных
if 'price_data' not in st.session_state:
    st.session_state.price_data = load_default_data()
if 'last_upload' not in st.session_state:
    st.session_state.last_upload = None
if 'repair_history' not in st.session_state:
    st.session_state.repair_history = pd.DataFrame(columns=[
        "Дата", "Наряд", "Бренд", "Модель Машины", "SN Машины",
        "Префикс Заказчик", "Назв цилиндра", "SN цилиндра",
        "#Трубы", "#Штока", "#Поршня", "#Головы",
        "Стоимость материалов (KZT)", "Стоимость работ (KZT)",
        "Итоговая стоимость (KZT)", "Итоговая стоимость (USD)"
    ])


# Управление ценами
def price_management():
    st.header("📊 Управление ценами на материалы")

    uploaded_file = st.file_uploader("Загрузите файл с ценами (Excel или CSV)", type=["xlsx", "csv"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                new_data = pd.read_excel(uploaded_file)
            else:
                try:
                    new_data = pd.read_csv(uploaded_file)
                except:
                    uploaded_file.seek(0)
                    new_data = pd.read_csv(uploaded_file, sep=';')

            required_columns = ["MaterialName", "Cost", "Units"]
            missing_cols = [col for col in required_columns if col not in new_data.columns]

            if not missing_cols:
                if "LastUpdated" not in new_data.columns:
                    new_data["LastUpdated"] = datetime.now().date()
                st.session_state.price_data = new_data
                st.session_state.last_upload = datetime.now()
                st.success("Данные успешно загружены!")
            else:
                st.error(f"Отсутствуют колонки: {', '.join(missing_cols)}")
        except Exception as e:
            st.error(f"Ошибка при загрузке: {str(e)}")

    with st.expander("✏️ Текущие данные о ценах", expanded=True):
        if st.session_state.price_data.empty:
            st.warning("Нет данных для отображения")
        else:
            edited_data = st.data_editor(
                st.session_state.price_data,
                column_config={
                    "Cost": st.column_config.NumberColumn("Цена (KZT)", min_value=0, format="%.0f"),
                    "LastUpdated": st.column_config.DateColumn("Обновлено", format="DD.MM.YYYY", disabled=True)
                },
                num_rows="dynamic"
            )
            if st.button("Сохранить изменения"):
                if not edited_data.equals(st.session_state.price_data):
                    mask = edited_data.ne(st.session_state.price_data).any(axis=1)
                    edited_data.loc[mask, "LastUpdated"] = datetime.now().date()
                    st.session_state.price_data = edited_data
                    st.success("Изменения сохранены!")


# Функция для извлечения диаметра из названия материала
def extract_diameter(material_name):
    match = re.search(r'Ø(\d+)', material_name)
    return int(match.group(1)) if match else None


# Основной калькулятор
def main_calculator():
    st.title("🔧 Калькулятор ремонта гидроцилиндров")

    with st.form("repair_form"):
        st.subheader("📝 Вводные данные о ремонте")
        col1, col2 = st.columns(2)

        with col1:
            job_order = st.text_input("Наряд")
            brand = st.text_input("Бренд")
            model = st.text_input("Модель Машины")
            sn_machine = st.text_input("SN Машины")
            prefix = st.text_input("Префикс Заказчик")

        with col2:
            client = st.text_input("Название цилиндра")
            sn_cylinder = st.text_input("SN цилиндра")
            pipe_num = st.text_input("# Трубы")
            rod_num = st.text_input("# Штока")
            piston_num = st.text_input("# Поршня")
            head_num = st.text_input("# Головы")

        st.subheader("📦 Материалы")
        col3, col4, col5 = st.columns(3)

        with col3:
            tube_options = st.session_state.price_data[
                st.session_state.price_data['MaterialName'].str.contains('Труба|труба', case=False)
            ]
            if not tube_options.empty:
                tube_selection = st.selectbox("Труба", tube_options['MaterialName'])
                tube_data = tube_options[tube_options['MaterialName'] == tube_selection].iloc[0]
                tube_length = st.number_input("Длина трубы (м)", min_value=0.1, value=1.0, step=0.1)
            else:
                st.warning("Нет данных о трубах")

        with col4:
            rod_options = st.session_state.price_data[
                st.session_state.price_data['MaterialName'].str.contains('Шток|шток', case=False)
            ]
            if not rod_options.empty:
                rod_selection = st.selectbox("Шток", rod_options['MaterialName'])
                rod_data = rod_options[rod_options['MaterialName'] == rod_selection].iloc[0]
                rod_length = st.number_input("Длина штока (м)", min_value=0.1, value=1.0, step=0.1)
            else:
                st.warning("Нет данных о штоках")

        with col5:
            # Получаем все материалы типа "Кругляк" для поршня
            piston_options = st.session_state.price_data[
                st.session_state.price_data['MaterialName'].str.contains('Кругляк|кругляк', case=False)
            ]

            if not piston_options.empty:
                # Сортируем по диаметру
                piston_options = piston_options.copy()
                piston_options['Diameter'] = piston_options['MaterialName'].apply(extract_diameter)
                piston_options = piston_options.sort_values('Diameter')

                piston_selection = st.selectbox("Материал поршня (кругляк)", piston_options['MaterialName'])
                piston_data = piston_options[piston_options['MaterialName'] == piston_selection].iloc[0]
                piston_diameter = extract_diameter(piston_selection)

                st.markdown(f"**Диаметр поршня:** {piston_diameter} мм")
                piston_length = st.number_input("Длина поршня (мм)", min_value=10, value=100, step=5)
                piston_quantity = st.number_input("Количество поршней", min_value=1, value=1, step=1)
            else:
                st.warning("Нет данных о материалах для поршней (кругляк)")

        st.subheader("🛠 Трудозатраты")
        col6, col7, col8 = st.columns(3)
        with col6:
            hours_inspection = st.number_input("Часы на приемку/разборку", min_value=0.5, value=2.0, step=0.5)
            hours_assembly = st.number_input("Часы на сборку/отправку", min_value=0.5, value=1.5, step=0.5)
        with col7:
            hours_liner = st.number_input("Часы на изготовление гильзы", min_value=0.5, value=4.0, step=0.5)
            hours_rod = st.number_input("Часы на изготовление штока", min_value=0.5, value=3.0, step=0.5)
        with col8:
            hours_piston = st.number_input("Часы на изготовление поршня", min_value=0.5, value=3.5, step=0.5)

        st.subheader("💰 Финансовые параметры")
        col9, col10 = st.columns(2)
        with col9:
            usd_rate = st.number_input("Курс USD/KZT", min_value=1, value=450)
            vat = st.number_input("НДС (%)", min_value=0, max_value=20, value=12)
        with col10:
            workshop_rate = st.number_input("Ставка цеха (KZT/час)", min_value=1000, value=5000)
            margin = st.slider("Маржа (%)", min_value=0, max_value=100, value=25)

        submitted = st.form_submit_button("Рассчитать")

    if submitted:
        if 'tube_data' not in locals() or 'rod_data' not in locals() or 'piston_data' not in locals():
            st.error("Пожалуйста, загрузите данные о материалах")
            return

        # Расчет стоимости материалов
        tube_cost_kzt = tube_data['Cost'] * tube_length
        rod_cost_kzt = rod_data['Cost'] * rod_length
        piston_cost_kzt = piston_data['Cost'] * (piston_length / 1000) * piston_quantity  # переводим мм в метры
        materials_cost_kzt = tube_cost_kzt + rod_cost_kzt + piston_cost_kzt

        # Расчет стоимости работ
        labor_hours = hours_inspection + hours_liner + hours_rod + hours_piston + hours_assembly
        labor_cost_kzt = labor_hours * workshop_rate

        # Итоговый расчет
        subtotal_kzt = materials_cost_kzt + labor_cost_kzt
        price_with_margin = subtotal_kzt * (1 + margin / 100)
        final_price_kzt = price_with_margin * (1 + vat / 100)
        final_price_usd = final_price_kzt / usd_rate

        # Сохранение в историю
        new_record = pd.DataFrame([{
            "Дата": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "Наряд": job_order,
            "Бренд": brand,
            "Модель Машины": model,
            "SN Машины": sn_machine,
            "Префикс Заказчик": prefix,
            "Назв цилиндра": client,
            "SN цилиндра": sn_cylinder,
            "#Трубы": pipe_num,
            "#Штока": rod_num,
            "#Поршня": piston_num,
            "#Головы": head_num,
            "Стоимость материалов (KZT)": materials_cost_kzt,
            "Стоимость работ (KZT)": labor_cost_kzt,
            "Итоговая стоимость (KZT)": final_price_kzt,
            "Итоговая стоимость (USD)": final_price_usd
        }])

        st.session_state.repair_history = pd.concat(
            [st.session_state.repair_history, new_record],
            ignore_index=True
        )

        # Вывод результатов
        st.header("📊 Результаты расчета")

        st.subheader("📦 Материалы")
        col11, col12, col13 = st.columns(3)
        with col11:
            st.markdown(f"""
            **{tube_selection}**  
            - Длина: {tube_length} м  
            - Цена: {tube_data['Cost']} KZT/м  
            - Стоимость: {tube_cost_kzt:.0f} KZT
            """)
        with col12:
            st.markdown(f"""
            **{rod_selection}**  
            - Длина: {rod_length} м  
            - Цена: {rod_data['Cost']} KZT/м  
            - Стоимость: {rod_cost_kzt:.0f} KZT
            """)
        with col13:
            st.markdown(f"""
            **{piston_selection}**  
            - Диаметр: {piston_diameter} мм  
            - Длина: {piston_length} мм  
            - Количество: {piston_quantity} шт  
            - Цена: {piston_data['Cost']} KZT/м  
            - Стоимость: {piston_cost_kzt:.0f} KZT
            """)
        st.markdown(f"**Итого по материалам:** {materials_cost_kzt:.0f} KZT")

        st.subheader("🛠 Работы")
        st.markdown(f"""
        - Всего часов: {labor_hours:.1f} ч  
        - Ставка: {workshop_rate} KZT/ч  
        - Стоимость работ: {labor_cost_kzt:.0f} KZT
        """)

        st.subheader("💰 Финальный расчет")
        st.markdown(f"""
        - Материалы: {materials_cost_kzt:.0f} KZT  
        - Работы: {labor_cost_kzt:.0f} KZT  
        - Себестоимость: {subtotal_kzt:.0f} KZT  
        - + Маржа {margin}%: ×{(1 + margin / 100):.2f}  
        - + НДС {vat}%: ×{(1 + vat / 100):.2f}  
        - **Итого:** {final_price_kzt:.0f} KZT = {final_price_usd:.2f} USD
        """)

        st.metric("Итоговая стоимость (KZT)", f"{final_price_kzt:,.0f} ₸")
        st.metric("Итоговая стоимость (USD)", f"{final_price_usd:,.2f} $")

        # Экспорт текущего расчета
        export_data = pd.DataFrame({
            "Позиция": ["Труба", "Шток", "Поршень", "Работы", "Итог"],
            "Стоимость (KZT)": [tube_cost_kzt, rod_cost_kzt, piston_cost_kzt, labor_cost_kzt, final_price_kzt],
            "Стоимость (USD)": [
                tube_cost_kzt / usd_rate,
                rod_cost_kzt / usd_rate,
                piston_cost_kzt / usd_rate,
                labor_cost_kzt / usd_rate,
                final_price_usd
            ],
            "Дата обновления": [
                tube_data["LastUpdated"],
                rod_data["LastUpdated"],
                piston_data["LastUpdated"],
                "-",
                "-"
            ]
        })

        st.download_button(
            label="📥 Скачать текущий расчёт (CSV)",
            data=export_data.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"repair_{job_order if job_order else datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

    # Отображение истории
    st.header("📜 История ремонтов")
    if not st.session_state.repair_history.empty:
        st.dataframe(
            st.session_state.repair_history,
            column_config={
                "Дата": st.column_config.DatetimeColumn(format="DD.MM.YYYY HH:mm"),
                "Стоимость материалов (KZT)": st.column_config.NumberColumn(format="%.0f ₸"),
                "Стоимость работ (KZT)": st.column_config.NumberColumn(format="%.0f ₸"),
                "Итоговая стоимость (KZT)": st.column_config.NumberColumn(format="%.0f ₸"),
                "Итоговая стоимость (USD)": st.column_config.NumberColumn(format="%.2f $")
            },
            use_container_width=True,
            hide_index=True
        )

        # Экспорт всей истории
        st.download_button(
            label="📥 Скачать всю историю (CSV)",
            data=st.session_state.repair_history.to_csv(index=False).encode('utf-8-sig'),
            file_name="repair_history.csv",
            mime="text/csv"
        )
    else:
        st.info("История ремонтов пуста")


# Запуск приложения
if __name__ == "__main__":
    price_management()
    main_calculator()
