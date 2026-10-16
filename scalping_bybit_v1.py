import sys
import pandas as pd
import pickle
from PyQt5 import QtWidgets
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots
from PyQt5 import QtCore
import pytz

# Глобальные переменные для диапазона дат
global_start_date = "2023-12-18"
global_end_date = "2024-01-05"

# Загрузка и обработка данных
def load_data():
    # with open('dataframe_btc_5m_all.pkl', 'rb') as file:
    # with open('dataframe_btc_1d.pkl', 'rb') as file:
    with open('dataframe_btc_5m_all.pkl', 'rb') as file:
        df = pickle.load(file)
        df = df.iloc[:, :6] # Обрезаем ненужные столбцы из датафрейма
        df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'] # Присваиваем имена столбцам

        # Преобразовываем временную метку в формат даты и убеждаемся, что все ohlcv имеют числовые значения
        df['Date'] = pd.to_datetime(df['Date'], unit='ms')

        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col])

        return df

# Функция для обработки и отображения данных
def process_and_display_data(df):
    global filtered_df, fig, global_start_date, global_end_date

    # Обработка данных
    df = df.iloc[:, :6]
    df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']

    # Преобразование из UTC в Московское время:
    df['Date'] = pd.to_datetime(df['Date'], unit='ms')
    # df['Date'] = pd.to_datetime(df['Date'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Europe/Moscow')

    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col])

    # Фильтрация данных с использованием глобальных переменных дат
    filtered_df = df.loc[(df['Date'] >= global_start_date) & (df['Date'] <= global_end_date)].copy()

    # Пересчет пин-баров и создание графика
    filtered_df['PinBar'] = filtered_df.apply(is_pin_bar, axis=1)
    fig = create_candlestick_graph(filtered_df)

    # # # Указываем имя файла, в который мы хотим записать данные и записываем датафрейм в Excel
    # excel_file = 'example.xlsx'
    # filtered_df.to_excel(excel_file, index=False)  # Если вы хотите сохранить индекс, удалите параметр index=False

    # Выводим отфильтрованный датафрейм
    print(filtered_df)

    # Отображение графика
    show_plot()

# Функция для загрузки дневных свечей (1d)
def load_daily_data():
    file_path = 'dataframe_btc_1d.pkl'
    with open(file_path, 'rb') as file:
        df = pickle.load(file)
        process_and_display_data(df)

# Функция для загрузки пятиминутных свечей (5m)
def load_5m_data():
    file_path = 'dataframe_btc_5m_all.pkl'
    with open(file_path, 'rb') as file:
        df = pickle.load(file)
        process_and_display_data(df)

# Функция для проверки наличия данных в новом диапазоне дат
def check_data_availability(df, start_date, end_date):
    min_date = df['Date'].min()
    max_date = df['Date'].max()
    return (pd.to_datetime(start_date) >= min_date) and (pd.to_datetime(end_date) <= max_date)

# Функция для изменения диапазона дат при нажатии на кнопку "Вперёд".
def move_month_forward():
    global global_start_date, global_end_date
    df = load_data()
    start_date = pd.to_datetime(global_start_date) + pd.DateOffset(days=10)
    end_date = pd.to_datetime(global_end_date) + pd.DateOffset(days=10)

    if check_data_availability(df, start_date, end_date):
        global_start_date = start_date.strftime('%Y-%m-%d')
        global_end_date = end_date.strftime('%Y-%m-%d')
        update_data_and_plot()
        update_text_widget()
    else:
        show_error_message("Данные за следующий месяц отсутствуют.")

# Функция для изменения диапазона дат при нажатии на кнопку "Назад".
def move_month_backward():
    global global_start_date, global_end_date
    df = load_data()
    start_date = pd.to_datetime(global_start_date) - pd.DateOffset(days=10)
    end_date = pd.to_datetime(global_end_date) - pd.DateOffset(days=10)

    if check_data_availability(df, start_date, end_date):
        global_start_date = start_date.strftime('%Y-%m-%d')
        global_end_date = end_date.strftime('%Y-%m-%d')
        update_data_and_plot()
        update_text_widget()
    else:
        show_error_message("Данные за предыдущий месяц отсутствуют.")

# Функция для отображения сообщения об ошибке
def show_error_message(message):
    error_dialog = QtWidgets.QMessageBox()
    error_dialog.setIcon(QtWidgets.QMessageBox.Warning)
    error_dialog.setText(message)
    error_dialog.setWindowTitle("Ошибка")
    error_dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
    error_dialog.exec_()

# Функция для обновления данных и графика
def update_data_and_plot():
    # Здесь вы можете загрузить данные и применить фильтр дат
    df = load_data()  # Загрузка данных
    process_and_display_data(df)

# Определение пин-баров
def is_pin_bar(row):
    body = abs(row['Close'] - row['Open'])
    upper_shadow = row['High'] - max(row['Close'], row['Open'])
    lower_shadow = min(row['Close'], row['Open']) - row['Low']

    # Условие для пин-бара: растущая свеча, нижняя тень длиннее тела и верхняя тень короче тела
    # return row['Close'] > row['Open'] and lower_shadow > body and upper_shadow < body

    # Условие для пин-бара: растущая свеча, нижняя тень в 1.5 раза длиннее тела, верхняя тень не более 90% тела
    return row['Close'] > row['Open'] and lower_shadow > 0.5 * body and upper_shadow < 0.9 * body


# Создание свечного графика
def create_candlestick_graph(df):
    # Создание субплотов
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.01,
                        row_heights=[0.7, 0.12])

    # Добавление свечей на график с использованием векторизации
    # Это значительно ускорит процесс, особенно если данных много
    pin_bars = filtered_df[filtered_df['PinBar']]
    non_pin_bars = filtered_df[~filtered_df['PinBar']]

    # Добавление не-пин-баров
    fig.add_trace(go.Candlestick(x=non_pin_bars['Date'],
                                 open=non_pin_bars['Open'],
                                 high=non_pin_bars['High'],
                                 low=non_pin_bars['Low'],
                                 close=non_pin_bars['Close'],
                                 showlegend=False))

    # Добавление пин-баров
    fig.add_trace(go.Candlestick(x=pin_bars['Date'],
                                 open=pin_bars['Open'],
                                 high=pin_bars['High'],
                                 low=pin_bars['Low'],
                                 close=pin_bars['Close'],
                                 increasing={'line': {'color': '#121212', 'width': 2},
                                             'fillcolor': '#121212'},
                                 decreasing={'line': {'color': '#121212', 'width': 2},
                                             'fillcolor': '#121212'},
                                 name='Пин-бар'))

    # Собираем данные для зелёных стрелок для пин-баров
    pin_bars = filtered_df[filtered_df['PinBar']]
    x_values = pin_bars['Date'].tolist()  # Даты для стрелок
    y_values = (pin_bars['Low'] * 0.999).tolist()  # Позиции стрелок (1% ниже нижней точки пин-бара)

    # Добавляем все стрелки одной трассировкой
    arrows = go.Scatter(x=x_values, y=y_values,
                        mode='markers',
                        marker=dict(color='green', size=8, symbol='arrow-up'),
                        name='Стрелочки')
    fig.add_trace(arrows)

    # Определение цветов для столбиков гистограммы объёмов
    colors = ['green' if row['Close'] >= row['Open'] else 'red' for index, row in df.iterrows()]

    # Добавление гистограммы объёмов
    fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=colors, showlegend=False), row=2, col=1)

    # Настройки визуализации
    customize_graph(fig)
    return fig

# Настройки визуализации графика
def customize_graph(fig):
    # Измените размеры графика и область просмотра (viewport)
    fig.update_layout(
        title='Свечной график',
        xaxis_rangeslider_visible=False,
        width=980,  # Ширина графика в пикселях
        height=810,  # Высота графика в пикселях
        # showlegend=False  # Скрывает легенду (боковую панель с метками трассировки)
    )

    # Установите отступы в макете графика, чтобы уменьшить поля
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0)  # Установите отступы (лево, право, верх, низ) в пикселях
    )

    # меняем шаг сетки по оси x и оси y
    fig.update_yaxes(nticks=40)
    fig.update_xaxes(nticks=50)

    # округляем значения по оси x
    fig.update_yaxes(tickformat=".0f")

    # делаем интерактивный курсор
    fig.update_yaxes(spikecolor='darkgray', spikedash='dot', spikemode='across', spikesnap='cursor', spikethickness=1)
    fig.update_xaxes(spikecolor='darkgray', spikedash='dot', spikemode='across', spikesnap='cursor', spikethickness=1)

    # изменяем цвет фона
    fig.update_layout(plot_bgcolor='white')

    # изменяем цвет сетки
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F0F0F0')

    # добавляем утолщение и цвет для оси x и оси y (а также зеркально дублируем (mirror=True))
    fig.update_xaxes(showline=True, linewidth=2, linecolor='Silver', mirror=True)
    fig.update_yaxes(showline=True, linewidth=2, linecolor='Silver', mirror=True)

    # Настройка осей для гистограммы объёмов
    fig.update_yaxes(row=2, col=1)
    fig.update_xaxes(showgrid=True, gridcolor='#F8F6F6', nticks=60, row=2, col=1)  # Изменение сетки объёмов по горизонтали
    fig.update_yaxes(showgrid=True, gridcolor='#F8F6F6', nticks=9, row=2, col=1)  # Изменение сетки объёмов по вертикали

    # Устанавливаем размеры графика так, чтобы он занимал всю доступную область
    fig.update_xaxes(range=[filtered_df['Date'].min(), filtered_df['Date'].max()])

    # Форматируем дату (которая отображается на графике):
    # fig.update_xaxes(tickformat="%d.%m.%y, %H:%M")


# Создаем отдельный виджет для отображения текста
class TextWidget(QtWidgets.QWidget):
    def __init__(self, filtered_df):
        super().__init__()
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.init_ui(filtered_df)
        # Устанавливаем фиксированную ширину текстового виджета (в пикселях)
        self.setFixedWidth(400)  # Замените на желаемую ширину

    def init_ui(self, filtered_df):
        # Определение начальных данных
        deposit = 100
        leverage = 5
        pnl = 2
        sdelki = 3
        time = 4
        profit = 220
        pinbar_count = filtered_df['PinBar'].sum()

        # Добавляем основные метки
        self.layout.addWidget(QtWidgets.QLabel('<b style="font-size: 12px;">Статистика сделок:</b>'), 0, 0, 1, 2)
        self.add_label(f'Депозит: {deposit} USDT', 1, 0)
        self.add_label(f'Плечо: x{leverage}', 1, 1)
        self.add_label(f'Прибыль: {pnl}%', 2, 0)
        self.add_label(f'Количество сделок: {sdelki}', 2, 1)
        self.add_label(f'Время в сделке: {time} дней', 3, 0)
        self.add_label(f'Общая прибыль: {profit} USDT', 3, 1)
        # Метка для количества пин-баров
        self.pinbar_label = QtWidgets.QLabel(f'Количество пин-баров: {pinbar_count} шт.')
        self.layout.addWidget(self.pinbar_label, 4, 0, 1, 2)  # Объединяем ячейки для этой метки

    def add_label(self, text, row, col):
        label = QtWidgets.QLabel(text)
        self.layout.addWidget(label, row, col)

    def update_text(self, filtered_df):
        # Обновляем количество пин-баров
        pinbar_count = filtered_df['PinBar'].sum()
        self.pinbar_label.setText(f'Количество пин-баров: {pinbar_count} шт.')


# Функция для обновления и отображения виджета с текстом
def update_text_widget():
    global text_widget, filtered_df
    text_widget.update_text(filtered_df)


# Переменные для хранения состояний отображения элементов графика
show_legend = False
show_pin_bars = True
show_arrows = True

# Вспомогательная функция для отображения графика в PyQt
def show_plot():
    fig.update_layout(showlegend=show_legend)  # Добавьте это, чтобы синхронизировать состояние легенды с переменной
    raw_html = '<html><head><meta charset="utf-8" /></head><body>'
    raw_html += plot(fig, output_type='div', include_plotlyjs='cdn')
    raw_html += '</body></html>'
    browser.setHtml(raw_html)

# Функции для обработки изменений чекбоксов
def toggle_legend():
    global show_legend
    show_legend = not show_legend
    fig.update_layout(showlegend=show_legend)
    show_plot()

def toggle_pin_bars():
    global show_pin_bars
    show_pin_bars = not show_pin_bars
    for trace in fig.data:
        if trace.name == 'Пин-бар':
            trace.visible = show_pin_bars
    show_plot()

def toggle_arrows():
    global show_arrows
    show_arrows = not show_arrows
    for trace in fig.data:
        if trace.name == 'Стрелочки':
            trace.visible = show_arrows
    show_plot()


# Функция для обновления размеров графика при изменении размера окна
def resize_event(event):
    # Получаем новые размеры окна
    width = event.size().width()
    height = event.size().height()

    # Обновляем размеры графика
    fig.update_layout(
        width=width - 50,  # Учитываем отступы
        height=height - 169,  # Учитываем отступы
    )
    show_plot()


global_table_window = None

# Функция для отображения данных в таблице
def show_table():
    global global_table_window

    # Создание виджета таблицы
    table_widget = QtWidgets.QTableWidget()
    table_widget.setRowCount(len(filtered_df))
    table_widget.setColumnCount(len(filtered_df.columns))
    table_widget.setHorizontalHeaderLabels(filtered_df.columns)

    # Заполнение таблицы данными
    for i, (index, row) in enumerate(filtered_df.iterrows()):
        for j, value in enumerate(row):
            cell = QtWidgets.QTableWidgetItem(str(value))
            table_widget.setItem(i, j, cell)

    # Показ таблицы в новом окне
    global_table_window = QtWidgets.QWidget()
    global_table_window.setWindowTitle("Filtered Data Table")
    layout = QtWidgets.QVBoxLayout()
    layout.addWidget(table_widget)
    global_table_window.setLayout(layout)
    global_table_window.resize(800, 600)
    global_table_window.show()

# Создаем главное окно приложения
app = QtWidgets.QApplication(sys.argv)
window = QtWidgets.QMainWindow()

# Устанавливаем обработчик события изменения размера окна
window.resizeEvent = resize_event

# Создание и настройка центрального виджета и его макета
central_widget = QtWidgets.QWidget()
central_layout = QtWidgets.QVBoxLayout()
central_widget.setLayout(central_layout)

# Создаем горизонтальный бокс для чекбоксов
controls_layout = QtWidgets.QHBoxLayout()

# Создаем чекбоксы
show_legend_checkbox = QtWidgets.QCheckBox('Показать легенду')
show_legend_checkbox.setChecked(False)  # Изменено на False
show_legend_checkbox.stateChanged.connect(toggle_legend)

show_pin_bars_checkbox = QtWidgets.QCheckBox('Показать пин-бары')
show_pin_bars_checkbox.setChecked(True)
show_pin_bars_checkbox.stateChanged.connect(toggle_pin_bars)

show_arrows_checkbox = QtWidgets.QCheckBox('Показать стрелки')
show_arrows_checkbox.setChecked(True)
show_arrows_checkbox.stateChanged.connect(toggle_arrows)

# Добавляем кнопки для загрузки свечей
load_daily_button = QtWidgets.QPushButton('Таймфрейм 1D')
load_daily_button.clicked.connect(load_daily_data)
load_5m_button = QtWidgets.QPushButton('Таймфрейм 5m')
load_5m_button.clicked.connect(load_5m_data)

# Добавляем кнопки для перемещения по месяцам назад
month_back = QtWidgets.QPushButton('Назад')
month_back.clicked.connect(move_month_backward)
month_back.setStyleSheet("background-color: red; color: white;")    # Красный фон и белый текст

# Добавляем кнопки для перемещения по месяцам вперёд
month_next = QtWidgets.QPushButton('Вперёд')
month_next.clicked.connect(move_month_forward)
month_next.setStyleSheet("background-color: green; color: white;")  # Зеленый фон и белый текст

# Добавляем чекбоксы в горизонтальный бокс
controls_layout.addWidget(show_legend_checkbox)
controls_layout.addWidget(show_pin_bars_checkbox)
controls_layout.addWidget(show_arrows_checkbox)

# Добавляем кнопки загрузки данных в горизонтальный бокс
controls_layout.addWidget(load_daily_button)
controls_layout.addWidget(load_5m_button)
controls_layout.addWidget(month_back)
controls_layout.addWidget(month_next)
central_layout.addLayout(controls_layout)

# Добавляем горизонтальный бокс с чекбоксами и кнопками в верхнюю часть вертикального бокса
central_layout.addLayout(controls_layout)

# Создаем и добавляем виджет для графика
browser = QWebEngineView()

# Устанавливаем политику размера для виджета браузера, чтобы он занимал большую часть окна
browser.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

# Добавление виджет для графика в основной вертикальный макет
central_layout.addWidget(browser)

# --------------------

# Создание горизонтального макета для кнопки и текста
top_layout = QtWidgets.QHBoxLayout()

# Убедитесь, что эта функция вызывается до создания экземпляра TextWidget
df = load_data()
process_and_display_data(df)

# Создание и настройка виджета текста
text_widget = TextWidget(filtered_df)

# Добавление виджета текста в горизонтальный макет
top_layout.addWidget(text_widget)

# Устанавливаем фиксированную высоту для text_widget
desired_text_widget_height = 100  # Укажите желаемую высоту в пикселях
text_widget.setFixedHeight(desired_text_widget_height)

# Создание кнопки для отображения таблицы
show_table_button = QtWidgets.QPushButton("Показать таблицу")
show_table_button.clicked.connect(show_table)

# Добавление кнопки в горизонтальный макет
top_layout.addWidget(show_table_button, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

# Добавление горизонтального макета в основной вертикальный макет
central_layout.addLayout(top_layout)

# --------------------

# Настройка и отображение главного окна
window.setCentralWidget(central_widget)
window.setWindowTitle("Анализ финансовых данных")
window.resize(1030, 980) # Устанавливаем начальные размеры окна
window.show()
show_plot()

sys.exit(app.exec_())