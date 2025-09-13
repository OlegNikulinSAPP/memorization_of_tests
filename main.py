import wx
import sqlite3
import random
import wx.grid


# Создаем кастомный класс для текстового поля с автоматической высотой и переносом текста
class AutoWrapTextCtrl(wx.TextCtrl):
    def __init__(self, parent, *args, **kwargs):
        # Устанавливаем стили для многострочного текста с переносом
        kwargs['style'] = wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_DONTWRAP
        super().__init__(parent, *args, **kwargs)
        self.Bind(wx.EVT_TEXT, self.on_text_change)
        self.parent = parent
        self.min_height = 60  # Минимальная высота
        self.max_height = 300  # Максимальная высота

    def on_text_change(self, event):
        # Вычисляем необходимую высоту на основе содержимого
        text = self.GetValue()
        if not text:
            self.SetMinSize((-1, self.min_height))
        else:
            # Создаем временный DC для измерения текста
            dc = wx.ClientDC(self)
            dc.SetFont(self.GetFont())

            # Получаем ширину текстового поля
            width = self.GetSize().width - 20  # Учитываем отступы

            # Вычисляем высоту текста с учетом переноса
            text_height = dc.GetMultiLineTextExtent(text, width)[1]

            # Добавляем отступы
            padding = 30
            new_height = min(self.max_height, max(self.min_height, text_height + padding))

            # Устанавливаем новую высоту
            self.SetMinSize((-1, new_height))

            # Обновляем layout родительского контейнера
            if self.parent:
                self.parent.Layout()

        event.Skip()


class MainWindow(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Exam Application', size=(1000, 700))
        self.init_db()

        # Создание Notebook (вкладок)
        self.notebook = wx.Notebook(self)

        # Панель добавления вопросов
        self.add_question_panel = AddQuestionPanel(self.notebook, self)
        # Панель экзамена
        self.exam_panel = ExamPanel(self.notebook, self)
        # Панель управления вопросами
        self.manage_panel = ManageQuestionsPanel(self.notebook, self)

        self.notebook.AddPage(self.add_question_panel, "Добавить вопрос")
        self.notebook.AddPage(self.exam_panel, "Экзамен")
        self.notebook.AddPage(self.manage_panel, "Управление вопросами")

        self.Centre()
        self.Show()

        # Обработчик закрытия окна
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_close(self, event):
        """Закрытие соединения с БД при выходе"""
        if hasattr(self, 'conn'):
            self.conn.close()
        event.Skip()

    def init_db(self):
        """Инициализация базы данных с поддержкой нескольких правильных ответов"""
        self.conn = sqlite3.connect('questions.db')
        self.cursor = self.conn.cursor()

        # Создаем новую таблицу
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                option1 TEXT,
                option2 TEXT,
                option3 TEXT,
                option4 TEXT,
                option5 TEXT,
                option6 TEXT,
                correct TEXT
            )
        ''')

        self.conn.commit()


class AddQuestionPanel(wx.Panel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.option_texts = []  # Список для хранения текстовых полей
        self.option_checks = []  # Список для хранения флажков правильности
        self.editing_id = None  # ID вопроса для редактирования (None для нового вопроса)
        self.init_ui()

    def init_ui(self):
        # Основной контейнер с прокруткой
        self.scroll_panel = wx.ScrolledWindow(self)
        self.scroll_panel.SetScrollRate(0, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)

        # Поле вопроса (используем AutoWrapTextCtrl)
        question_sizer = wx.BoxSizer(wx.HORIZONTAL)
        question_sizer.Add(wx.StaticText(self.scroll_panel, label="Вопрос:"), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.question_text = AutoWrapTextCtrl(self.scroll_panel, size=(400, 60))
        question_sizer.Add(self.question_text, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(question_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Заголовок для вариантов ответов
        options_header = wx.StaticText(self.scroll_panel, label="Варианты ответов (отметьте правильные):")
        vbox.Add(options_header, 0, wx.ALL, 5)

        # Контейнер для вариантов ответов
        self.options_container = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.options_container, 1, wx.EXPAND | wx.ALL, 5)

        # Кнопки для управления вариантами ответов
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.add_option_btn = wx.Button(self.scroll_panel, label="Добавить вариант")
        self.add_option_btn.Bind(wx.EVT_BUTTON, self.on_add_option)
        btn_sizer.Add(self.add_option_btn, 0, wx.ALL, 5)

        self.remove_option_btn = wx.Button(self.scroll_panel, label="Удалить вариант")
        self.remove_option_btn.Bind(wx.EVT_BUTTON, self.on_remove_option)
        btn_sizer.Add(self.remove_option_btn, 0, wx.ALL, 5)

        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        # Информация о правильных ответах
        correct_info = wx.StaticText(self.scroll_panel,
                                     label="Правильные ответы: Отметьте флажки рядом с правильными ответами")
        vbox.Add(correct_info, 0, wx.ALL, 5)

        # Кнопка сохранения
        self.save_button = wx.Button(self.scroll_panel, label="Добавить вопрос")
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_question)
        vbox.Add(self.save_button, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.scroll_panel.SetSizer(vbox)

        # Основной sizer для панели
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.scroll_panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)

        # Добавляем начальные два варианта ответа
        self.add_option()
        self.add_option()

        # Устанавливаем минимальный размер для прокрутки
        self.scroll_panel.SetMinSize((700, 500))
        self.scroll_panel.Layout()

    def add_option(self):
        """Добавление нового поля для варианта ответа"""
        if len(self.option_texts) >= 6:  # Максимум 6 вариантов
            wx.MessageBox("Максимальное количество вариантов - 6", "Информация", wx.OK | wx.ICON_INFORMATION)
            return

        option_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Чекбокс для отметки правильности ответа
        option_check = wx.CheckBox(self.scroll_panel)
        self.option_checks.append(option_check)
        option_sizer.Add(option_check, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # Поле для текста варианта ответа
        option_label = wx.StaticText(self.scroll_panel, label=f"Вариант {len(self.option_texts) + 1}:")
        option_sizer.Add(option_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        option_text = AutoWrapTextCtrl(self.scroll_panel, size=(300, 40))
        option_sizer.Add(option_text, 1, wx.ALL | wx.EXPAND, 5)

        self.options_container.Add(option_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.option_texts.append(option_text)

        self.scroll_panel.Layout()
        self.scroll_panel.SetVirtualSize(self.options_container.GetMinSize())

    def remove_option(self):
        """Удаление последнего поля варианта ответа"""
        if len(self.option_texts) > 2:  # Минимально 2 варианта
            # Удаляем последний элемент из контейнера
            last_index = len(self.option_texts) - 1

            # Удаляем все элементы из последнего sizer'а
            item = self.options_container.GetItem(last_index)
            if item and item.GetSizer():
                item.GetSizer().Clear(True)

            # Удаляем сам sizer из контейнера
            self.options_container.Detach(last_index)

            # Удаляем из списков
            self.option_texts.pop()
            self.option_checks.pop()

            self.scroll_panel.Layout()
            self.scroll_panel.SetVirtualSize(self.options_container.GetMinSize())
        else:
            wx.MessageBox("Минимальное количество вариантов - 2", "Информация", wx.OK | wx.ICON_INFORMATION)

    def on_add_option(self, event):
        self.add_option()

    def on_remove_option(self, event):
        self.remove_option()

    def on_save_question(self, event):
        question = self.question_text.GetValue()
        options = [opt.GetValue() for opt in self.option_texts]

        # Проверяем, что все поля заполнены
        if not question or any(not opt for opt in options):
            wx.MessageBox("Заполните все поля!", "Ошибка", wx.OK | wx.ICON_ERROR)
            return

        # Проверяем, что выбран хотя бы один правильный ответ
        correct_options = []
        for i, check in enumerate(self.option_checks):
            if check.GetValue():
                correct_options.append(str(i + 1))

        if not correct_options:
            wx.MessageBox("Выберите хотя бы один правильный ответ!", "Ошибка", wx.OK | wx.ICON_ERROR)
            return

        correct = ",".join(correct_options)

        try:
            if self.editing_id is None:
                # Добавление нового вопроса
                # Формируем запрос с правильным количеством параметров
                columns = ["question"]
                values = [question]

                # Добавляем варианты ответов
                for i, option in enumerate(options):
                    columns.append(f"option{i + 1}")
                    values.append(option)

                # Добавляем NULL для отсутствующих вариантов
                for i in range(len(options), 6):
                    columns.append(f"option{i + 1}")
                    values.append(None)

                columns.append("correct")
                values.append(correct)

                # Создаем строку с плейсхолдерами
                placeholders = ",".join(["?"] * len(values))

                query = f"INSERT INTO questions ({', '.join(columns)}) VALUES ({placeholders})"
                self.main_window.cursor.execute(query, values)
                action = "добавлен"
            else:
                # Обновление существующего вопроса
                columns = ["question=?"]
                values = [question]

                # Добавляем варианты ответов
                for i, option in enumerate(options):
                    columns.append(f"option{i + 1}=?")
                    values.append(option)

                # Добавляем NULL для отсутствующих вариантов
                for i in range(len(options), 6):
                    columns.append(f"option{i + 1}=?")
                    values.append(None)

                columns.append("correct=?")
                values.append(correct)

                values.append(self.editing_id)

                query = f"UPDATE questions SET {', '.join(columns)} WHERE id=?"
                self.main_window.cursor.execute(query, values)
                action = "обновлен"

            self.main_window.conn.commit()

            # Обновляем списки вопросов на других панелях
            self.main_window.exam_panel.reload_questions()
            self.main_window.manage_panel.load_questions()

            # Очистка полей
            self.clear_form()

            wx.MessageBox(f"Вопрос {action}!", "Успех", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Ошибка: {str(e)}", "Ошибка", wx.OK | wx.ICON_ERROR)

    def clear_form(self):
        """Очистка формы"""
        self.question_text.Clear()

        # Очищаем контейнер вариантов
        self.options_container.Clear(True)
        self.option_texts = []
        self.option_checks = []

        # Добавляем начальные два варианта ответа
        self.add_option()
        self.add_option()

        # Сбрасываем режим редактирования
        self.set_editing_mode(None)

        self.scroll_panel.Layout()

    def set_editing_mode(self, question_id=None):
        """Переключение в режим редактирования"""
        self.editing_id = question_id

        if question_id is not None:
            # Загружаем данные вопроса для редактирования
            self.main_window.cursor.execute("SELECT * FROM questions WHERE id=?", (question_id,))
            question = self.main_window.cursor.fetchone()

            if question:
                # Заполняем поле вопроса
                self.question_text.SetValue(question[1])

                # Очищаем существующие варианты
                self.options_container.Clear(True)
                self.option_texts = []
                self.option_checks = []

                # Добавляем варианты ответов
                for i in range(2, 8):  # option1 находится в индексе 2, option6 - в индексе 7
                    if i < len(question) and question[i]:
                        self.add_option_with_value(question[i])

                # Устанавливаем правильные ответы
                correct_values = question[8].split(",") if question[8] else []
                for i, check in enumerate(self.option_checks):
                    if str(i + 1) in correct_values:
                        check.SetValue(True)

                # Меняем текст кнопки
                self.save_button.SetLabel("Обновить вопрос")

        else:
            # Режим добавления нового вопроса
            self.editing_id = None
            self.save_button.SetLabel("Добавить вопрос")

    def add_option_with_value(self, value):
        """Добавление варианта ответа с заданным значением"""
        if len(self.option_texts) >= 6:  # Максимум 6 вариантов
            return

        option_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Чекбокс для отметки правильности ответа
        option_check = wx.CheckBox(self.scroll_panel)
        self.option_checks.append(option_check)
        option_sizer.Add(option_check, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # Поле для текста варианта ответа
        option_label = wx.StaticText(self.scroll_panel, label=f"Вариант {len(self.option_texts) + 1}:")
        option_sizer.Add(option_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        option_text = AutoWrapTextCtrl(self.scroll_panel, size=(300, 40))
        option_text.SetValue(value)
        option_sizer.Add(option_text, 1, wx.ALL | wx.EXPAND, 5)

        self.options_container.Add(option_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.option_texts.append(option_text)

        self.scroll_panel.Layout()
        self.scroll_panel.SetVirtualSize(self.options_container.GetMinSize())


class ExamPanel(wx.Panel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.current_question = None
        self.check_boxes = []
        self.questions = []
        self.asked_question_ids = set()  # Множество ID заданных вопросов
        self.available_question_ids = set()  # Множество ID доступных вопросов
        self.init_ui()
        self.load_questions()

    def init_ui(self):
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        # Текст вопроса (используем многострочное текстовое поле только для чтения)
        self.question_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.TE_NO_VSCROLL
        )
        self.question_text.SetBackgroundColour(self.GetBackgroundColour())
        self.vbox.Add(self.question_text, 0, wx.EXPAND | wx.ALL, 10)

        # Инструкция
        self.instruction = wx.StaticText(self, label="Выберите все правильные ответы:")
        self.vbox.Add(self.instruction, 0, wx.ALL, 5)

        # Прокрутка для вариантов ответов
        self.scroll = wx.ScrolledWindow(self)
        self.scroll.SetScrollRate(0, 10)
        self.scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.scroll_sizer)

        self.vbox.Add(self.scroll, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопка проверки
        self.check_button = wx.Button(self, label="Проверить")
        self.check_button.Bind(wx.EVT_BUTTON, self.on_check_answer)
        self.vbox.Add(self.check_button, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        # Кнопка новой сессии (изначально скрыта)
        self.new_session_btn = wx.Button(self, label="Начать новую сессию")
        self.new_session_btn.Bind(wx.EVT_BUTTON, self.on_new_session)
        self.new_session_btn.Hide()
        self.vbox.Add(self.new_session_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.SetSizer(self.vbox)

    def clear_options(self):
        """Очистка предыдущих вариантов ответов"""
        for cb in self.check_boxes:
            cb.Destroy()
        self.check_boxes = []

        # Очищаем sizer
        self.scroll_sizer.Clear(True)

    def load_questions(self):
        """Загрузка всех вопросов из базы данных"""
        self.main_window.cursor.execute("SELECT * FROM questions")
        self.questions = self.main_window.cursor.fetchall()

        # Создаем множество ID всех доступных вопросов
        self.available_question_ids = {q[0] for q in self.questions}
        self.asked_question_ids = set()  # Сбрасываем множество заданных вопросов

        self.load_question()

    def reload_questions(self):
        """Перезагрузка вопросов из базы данных"""
        self.main_window.cursor.execute("SELECT * FROM questions")
        self.questions = self.main_window.cursor.fetchall()

        # Обновляем множество доступных вопросов
        self.available_question_ids = {q[0] for q in self.questions}
        # Не сбрасываем asked_question_ids, чтобы продолжить текущую сессию

        self.load_question()

    def get_random_question(self):
        """Получение случайного вопроса из доступных"""
        if not self.available_question_ids:
            return None

        # Выбираем случайный ID из доступных вопросов
        random_id = random.choice(list(self.available_question_ids))

        # Находим вопрос по ID
        for question in self.questions:
            if question[0] == random_id:
                return question

        return None

    def load_question(self):
        """Загрузка случайного вопроса из доступных вопросов"""
        self.clear_options()

        # Получаем случайный вопрос
        self.current_question = self.get_random_question()

        if self.current_question is None:
            # Все вопросы были заданы или нет доступных вопросов
            self.show_session_complete()
            return

        # Удаляем ID вопроса из доступных и добавляем в заданные
        question_id = self.current_question[0]
        self.available_question_ids.discard(question_id)
        self.asked_question_ids.add(question_id)

        # Собираем все непустые варианты ответов
        options = []
        for i in range(2, 8):  # option1 находится в индексе 2, option6 - в индексе 7
            if i < len(self.current_question) and self.current_question[i]:
                options.append((self.current_question[i], i - 1))  # (текст, исходный номер)

        if not options or len(options) < 2:
            # Если вопрос некорректный, пропускаем его и загружаем следующий
            self.load_question()
            return

        # Устанавливаем текст вопроса
        self.question_text.SetValue(self.current_question[1])

        # Перемешиваем варианты ответов
        random.shuffle(options)

        # Получаем правильные ответы
        correct_value = self.current_question[8]  # correct находится в индексе 8

        # Обрабатываем оба случая: когда correct - число и когда это строка
        if isinstance(correct_value, int):
            # Старый формат: одно число
            correct_answers = [correct_value]
        elif isinstance(correct_value, str):
            # Новый формат: строка с числами через запятую
            correct_answers = [int(x) for x in correct_value.split(",")] if correct_value else []
        else:
            correct_answers = []

        # Запоминаем, какие варианты являются правильными после перемешивания
        self.correct_indices = []
        for idx, (text, original_index) in enumerate(options):
            if original_index in correct_answers:
                self.correct_indices.append(idx)

        # Создаем чекбоксы для каждого варианта ответа
        self.check_boxes = []
        for i, (option_text, _) in enumerate(options):
            # Используем StaticText с переносом для текста варианта ответа
            option_sizer = wx.BoxSizer(wx.HORIZONTAL)
            cb = wx.CheckBox(self.scroll)
            option_sizer.Add(cb, 0, wx.ALL | wx.ALIGN_TOP, 5)

            # Создаем статический текст с переносом
            option_label = wx.StaticText(self.scroll, label=option_text, style=wx.ALIGN_LEFT)
            option_label.Wrap(350)  # Перенос текста по ширине
            option_sizer.Add(option_label, 1, wx.ALL | wx.EXPAND, 5)

            self.scroll_sizer.Add(option_sizer, 0, wx.EXPAND | wx.ALL, 5)
            self.check_boxes.append(cb)

        # Обновляем макет
        self.scroll_sizer.Layout()
        self.scroll.SetVirtualSize(self.scroll_sizer.GetMinSize())
        self.Layout()

        # Показываем элементы интерфейса
        self.instruction.Show()
        self.scroll.Show()
        self.check_button.Show()
        self.new_session_btn.Hide()

    def show_session_complete(self):
        """Отображение сообщения о завершении сессии"""
        self.question_text.SetValue(
            "Вы ответили на все доступные вопросы!\n\nНажмите 'Начать новую сессию', чтобы начать заново.")

        # Скрываем элементы интерфейса
        self.instruction.Hide()
        self.scroll.Hide()
        self.check_button.Hide()

        # Показываем кнопку новой сессии
        self.new_session_btn.Show()

        self.Layout()

    def on_check_answer(self, event):
        # Находим выбранные варианты
        selected_indices = []
        for i, cb in enumerate(self.check_boxes):
            if cb.GetValue():
                selected_indices.append(i)

        if not selected_indices:
            wx.MessageBox("Выберите хотя бы один ответ!", "Ошибка", wx.OK | wx.ICON_ERROR)
            return

        # Сравниваем с правильными индексами (после перемешивания)
        if set(selected_indices) == set(self.correct_indices):
            wx.MessageBox("Правильно! Все ответы верные.", "Результат", wx.OK | wx.ICON_INFORMATION)
        else:
            # Формируем список правильных ответов
            correct_texts = []
            for i in self.correct_indices:
                # Получаем текст из StaticText
                option_sizer = self.scroll_sizer.GetItem(i).GetSizer()
                if option_sizer and option_sizer.GetItemCount() > 1:
                    option_label = option_sizer.GetItem(1).GetWindow()
                    if isinstance(option_label, wx.StaticText):
                        correct_texts.append(option_label.GetLabel())

            correct_str = "\n- ".join(correct_texts)
            wx.MessageBox(f"Неправильно!\n\nПравильные ответы:\n- {correct_str}",
                          "Результат", wx.OK | wx.ICON_ERROR)

        # Загружаем следующий вопрос
        self.load_question()

    def on_new_session(self, event):
        """Начало новой экзаменационной сессии"""
        # Восстанавливаем все вопросы как доступные
        self.available_question_ids = {q[0] for q in self.questions}
        self.asked_question_ids = set()  # Очищаем множество заданных вопросов
        self.load_question()  # Загружаем первый вопрос новой сессии

class ManageQuestionsPanel(wx.Panel):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.init_ui()
        self.load_questions()

    def init_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Заголовок
        title = wx.StaticText(self, label="Управление вопросами")
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        vbox.Add(title, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Список вопросов с детальной информацией
        self.questions_list = wx.ListCtrl(self, style=wx.LC_REPORT, size=(700, 400))
        self.questions_list.InsertColumn(0, "ID", width=50)
        self.questions_list.InsertColumn(1, "Вопрос", width=300)
        self.questions_list.InsertColumn(2, "Варианты ответов", width=300)
        self.questions_list.InsertColumn(3, "Правильные ответы", width=100)
        vbox.Add(self.questions_list, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопки управления
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        edit_btn = wx.Button(self, label="Редактировать")
        edit_btn.Bind(wx.EVT_BUTTON, self.on_edit_question)
        btn_sizer.Add(edit_btn, 0, wx.ALL, 5)

        delete_btn = wx.Button(self, label="Удалить")
        delete_btn.Bind(wx.EVT_BUTTON, self.on_delete_question)
        btn_sizer.Add(delete_btn, 0, wx.ALL, 5)

        refresh_btn = wx.Button(self, label="Обновить")
        refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        btn_sizer.Add(refresh_btn, 0, wx.ALL, 5)

        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(vbox)

    def load_questions(self):
        """Загрузка вопросов из базы данных и отображение в списке"""
        self.questions_list.DeleteAllItems()

        # Загружаем вопросы из базы
        self.main_window.cursor.execute("SELECT * FROM questions ORDER BY id")
        questions = self.main_window.cursor.fetchall()

        # Добавляем вопросы в список
        for question in questions:
            index = self.questions_list.InsertItem(self.questions_list.GetItemCount(), str(question[0]))
            self.questions_list.SetItem(index, 1, question[1])  # Вопрос

            # Формируем текст вариантов ответов
            options_text = ""
            for i in range(2, 8):
                if i < len(question) and question[i]:
                    options_text += f"{i - 1}. {question[i]}\n"
            self.questions_list.SetItem(index, 2, options_text.strip())

            # Правильные ответы
            self.questions_list.SetItem(index, 3, question[8] if len(question) > 8 else "")

    def get_selected_question_id(self):
        """Получение ID выбранного вопроса"""
        selection = self.questions_list.GetFirstSelected()
        if selection == -1:
            return None
        return int(self.questions_list.GetItemText(selection))

    def on_edit_question(self, event):
        """Редактирование выбранного вопроса"""
        question_id = self.get_selected_question_id()
        if question_id is None:
            wx.MessageBox("Выберите вопрос для редактирования!", "Внимание", wx.OK | wx.ICON_INFORMATION)
            return

        # Переключаемся на вкладку добавления вопросов
        self.main_window.notebook.SetSelection(0)

        # Устанавливаем режим редактирования
        self.main_window.add_question_panel.set_editing_mode(question_id)

    def on_delete_question(self, event):
        """Удаление выбранного вопроса"""
        question_id = self.get_selected_question_id()
        if question_id is None:
            wx.MessageBox("Выберите вопрос для удаления!", "Внимание", wx.OK | wx.ICON_INFORMATION)
            return

        # Подтверждение удаления
        confirm = wx.MessageBox("Вы уверены, что хотите удалить этот вопрос?",
                                "Подтверждение удаления",
                                wx.YES_NO | wx.ICON_QUESTION)

        if confirm == wx.YES:
            try:
                # Удаляем вопрос из базы данных
                self.main_window.cursor.execute("DELETE FROM questions WHERE id=?", (question_id,))
                self.main_window.conn.commit()

                # Обновляем списки вопросов на других панелях
                self.main_window.exam_panel.reload_questions()
                self.load_questions()

                wx.MessageBox("Вопрос удален!", "Успех", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"Ошибка при удалении: {str(e)}", "Ошибка", wx.OK | wx.ICON_ERROR)

    def on_refresh(self, event):
        """Обновление списка вопросов"""
        self.load_questions()
        wx.MessageBox("Список вопросов обновлен!", "Информация", wx.OK | wx.ICON_INFORMATION)

if __name__ == "__main__":
    app = wx.App()
    frame = MainWindow()
    app.MainLoop()