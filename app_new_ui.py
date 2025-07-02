# app_new_ui.py
"""
Главный файл приложения SysAdmin Assistant с графическим интерфейсом на PyQt5.
Стабильная версия с динамическими формами и NLU.
"""
import sys
import os
import re
from functools import partial

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QLabel, QSplitter, QTreeWidget,
    QTreeWidgetItem, QFormLayout, QDialog, QDialogButtonBox, QMessageBox,
    QInputDialog, QComboBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCursor, QTextCharFormat

# --- Импорт компонентов ---
from auth_rbac import AuthManager, Role
from command_templates import CommandTemplates
from logging_audit import AuditLogger
from utils import AdvancedNLUParser
from sysadmin_actions import execute_intent, DATA_PROVIDERS
import icon
from spinner import SpinnerWidget

# --- Константы и стили ---
COMMANDS_FILE = "commands.json"
STYLESHEET = """
    QMainWindow, QDialog { background-color: #36393f; }
    QWidget { color: #dcddde; font-family: "Segoe UI", "Cantarell", sans-serif; font-size: 10pt; }
    QTreeWidget {
        background-color: #2f3136; border: none; font-size: 11pt; outline: 0;
    }
    QTreeWidget::item { padding: 8px 10px; border-radius: 4px; }
    QTreeWidget::item:hover { background-color: #3a3c43; }
    QTreeWidget::item:selected { background-color: #40444b; color: #ffffff; }
    QTreeWidget::branch { image: none; }
    QLineEdit, QComboBox {
        background-color: #202225; border: 1px solid #202225;
        border-radius: 4px; padding: 8px; color: #dcddde;
    }
    QLineEdit:focus, QComboBox:focus { border-color: #7289da; }
    QLineEdit[validationState="invalid"] { border: 1px solid #f04747; }
    QLineEdit[validationState="valid"] { border: 1px solid #43b581; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView {
        background-color: #2f3136; border: 1px solid #40444b;
        selection-background-color: #40444b; outline: 0;
    }
    QTextEdit {
        background-color: #202225; border: 1px solid #40444b;
        border-radius: 4px; color: #dcddde;
        font-family: "Consolas", "Courier New", monospace;
    }
    QSplitter::handle { background-color: #202225; }
    QSplitter::handle:hover { background-color: #7289da; }
    QLabel#title_label { font-size: 14pt; font-weight: bold; color: #ffffff; }
"""
CATEGORY_TRANSLATIONS = {
    "Network": "Сеть", "System": "Система", "Process": "Процессы",
    "Disk": "Диски", "Software": "Программы", "Users": "Пользователи",
    "Services": "Службы", "Logs": "Логи и Журналы", "Fs": "Файловая система",
    "Power": "Питание",
}
INTENT_ICONS = {
    'network.get_ip_config': 'network-wired', 'network.change_ip_static': 'preferences-system-network',
    'process.list': 'view-process-tree', 'process.kill': 'process-stop',
    'disk.usage': 'drive-harddisk', 'disk.list_partitions': 'drive-multidisk',
    'services.control': 'preferences-system-windows-services', 'power.reboot': 'system-reboot',
    'power.shutdown': 'system-shutdown',
}


class Worker(QObject):
    finished = pyqtSignal()
    output = pyqtSignal(str)

    def __init__(self, intent, params, command_templates):
        super().__init__()
        self.intent, self.params, self.command_templates = intent, params, command_templates

    def run(self):
        execute_intent(self.intent, self.params, self.command_templates, self.output.emit)
        self.finished.emit()


class AnimatedButton(QPushButton):
    # ... (код остается без изменений) ...
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._color, self.hover_color, self.default_color, self.disabled_color = QColor("#5865f2"), QColor(
            "#4752c4"), QColor("#5865f2"), QColor("#4f545c")
        self.animation = QPropertyAnimation(self, b"buttonColor", self)
        self.animation.setDuration(200);
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.buttonColor = self.default_color

    def enterEvent(self, event):
        if self.isEnabled(): self.animation.setEndValue(self.hover_color); self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled(): self.animation.setEndValue(self.default_color); self.animation.start()
        super().leaveEvent(event)

    def setEnabled(self, enabled):
        super().setEnabled(enabled);
        self.animation.stop()
        self.buttonColor = self.default_color if enabled else self.disabled_color

    @pyqtProperty(QColor)
    def buttonColor(self):
        return self._color

    @buttonColor.setter
    def buttonColor(self, color):
        self._color = color
        self.setStyleSheet(
            f"background-color: {color.name()}; color: #ffffff; border: none; padding: 8px 16px; border-radius: 4px; font-weight: 500;")


class LoginDialog(QDialog):
    # ... (код остается без изменений) ...
    def __init__(self, auth_manager: AuthManager, parent=None):
        super().__init__(parent)
        self.auth_manager, self.user_role, self.username = auth_manager, None, ""
        self.setWindowTitle("Вход в SysAdmin Assistant");
        self.setMinimumWidth(350)
        layout, form_layout = QVBoxLayout(self), QFormLayout()
        self.username_input, self.password_input = QLineEdit(self), QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.username_input.setPlaceholderText("Имя пользователя")
        self.password_input.setPlaceholderText("Пароль")
        form_layout.addRow("Пользователь:", self.username_input)
        form_layout.addRow("Пароль:", self.password_input)
        layout.addLayout(form_layout)
        self.status_label = QLabel("");
        self.status_label.setStyleSheet("color: #f04747;")
        layout.addWidget(self.status_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.handle_login);
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.password_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        self.username, password = self.username_input.text().strip(), self.password_input.text()
        if not self.username or not password:
            self.status_label.setText("Имя пользователя и пароль не могут быть пустыми.");
            return
        role = self.auth_manager.verify_user(self.username, password)
        if role:
            self.user_role = role
            self.accept()
        else:
            self.status_label.setText("Неверное имя пользователя или пароль.")


class MainWindow(QMainWindow):
    def __init__(self, username: str, user_role: Role, auth_manager: AuthManager):
        super().__init__()
        self.username, self.user_role = username, user_role
        self.auth_manager = auth_manager
        self.command_templates = CommandTemplates()
        try:
            self.command_templates.load_from_json(COMMANDS_FILE)
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Не удалось загрузить '{COMMANDS_FILE}':\n{e}");
            sys.exit(1)

        self.nlu_parser = AdvancedNLUParser(self.command_templates)
        self.logger = AuditLogger()
        self.current_intent = None
        self.param_widgets = {}
        self.exec_thread, self.exec_worker = None, None

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("SysAdmin Assistant");
        self.setGeometry(100, 100, 1200, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0);
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # --- Левая панель (дерево команд) ---
        self.function_tree = QTreeWidget()
        self.function_tree.setHeaderHidden(True)
        self.function_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.populate_function_tree()
        splitter.addWidget(self.function_tree)

        # --- Правая панель (форма и консоль) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 10, 20, 10)

        # NLU-ввод
        nlu_area_layout = QHBoxLayout()
        self.nlu_input = QLineEdit();
        self.nlu_input.setPlaceholderText("Введите команду на русском языке...")
        self.nlu_input.returnPressed.connect(self.execute_from_nlu)
        self.spinner = SpinnerWidget();
        self.spinner.hide()
        nlu_area_layout.addWidget(self.nlu_input);
        nlu_area_layout.addWidget(self.spinner)
        right_layout.addLayout(nlu_area_layout)

        # Динамическая форма для параметров
        self.form_title = QLabel("Выберите команду")
        self.form_title.setObjectName("title_label")
        right_layout.addWidget(self.form_title)
        self.param_form_layout = QFormLayout()
        right_layout.addLayout(self.param_form_layout)

        self.form_execute_button = AnimatedButton("Выполнить команду")
        self.form_execute_button.clicked.connect(self.execute_from_form)
        self.form_execute_button.hide()
        right_layout.addWidget(self.form_execute_button, 0, Qt.AlignLeft)

        right_layout.addStretch(1)  # Пространство между формой и консолью

        # Консоль вывода
        self.output_console = QTextEdit();
        self.output_console.setReadOnly(True)
        right_layout.addWidget(self.output_console, 5)  # Увеличиваем долю консоли

        splitter.addWidget(right_panel)
        splitter.setSizes([280, 920])

    def populate_function_tree(self):
        self.function_tree.clear()
        categories = {}
        for intent, template in self.command_templates.intents.items():
            category_key = intent.split('.')[0].capitalize()
            if category_key not in categories: categories[category_key] = []
            categories[category_key].append(template)

        for category_key, templates in sorted(categories.items()):
            category_name = CATEGORY_TRANSLATIONS.get(category_key, category_key)
            category_item = QTreeWidgetItem(self.function_tree, [category_name])
            category_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
            for template in sorted(templates, key=lambda t: t.description):
                child_item = QTreeWidgetItem(category_item, [template.description])
                icon_name = INTENT_ICONS.get(template.intent, 'application-x-executable')
                child_item.setIcon(0, QIcon.fromTheme(icon_name))
                child_item.setData(0, Qt.UserRole, template.intent)
            category_item.setExpanded(True)

    def on_tree_item_clicked(self, item, column):
        intent = item.data(0, Qt.UserRole)
        if not intent:
            self.clear_param_form()
            self.form_title.setText("Выберите команду")
            return

        template = self.command_templates.get_intent_template(intent)
        if not template: return

        self.current_intent = intent
        self.form_title.setText(template.description)
        self.clear_param_form()

        if not template.params:
            self.run_execution(intent, {})
        else:
            self.create_param_form(template)
            self.form_execute_button.show()

    def create_param_form(self, template):
        """Создает динамическую форму на основе шаблона интента."""
        for name, spec in template.params.items():
            label_text = f"{name.replace('_', ' ').capitalize()}{' *' if spec.required else ''}:"
            widget = None

            if spec.type.startswith("choice"):
                widget = QComboBox()
                provider = DATA_PROVIDERS.get(spec.type)
                if provider:
                    try:
                        items = provider()
                        if not items:
                            widget.addItem(f"Не удалось получить данные")
                            widget.setEnabled(False)
                        elif spec.type == "choice_process":
                            widget.addItems([f"{p['pid']} - {p['name']}" for p in items])
                        elif spec.type == "choice_service":
                            widget.addItems([f"{s['name']} ({s['status']})" for s in items])
                        else:
                            widget.addItems(items)
                    except Exception as e:
                        widget.addItem(f"Ошибка: {e}")
                        widget.setEnabled(False)
                elif spec.choices:
                    widget.addItems(spec.choices)
            elif spec.type == "password":
                widget = QLineEdit()
                widget.setEchoMode(QLineEdit.Password)
            elif spec.type == "filepath":
                container = QWidget()
                hbox = QHBoxLayout(container)
                hbox.setContentsMargins(0, 0, 0, 0)
                file_path_edit = QLineEdit()
                browse_button = QPushButton("...");
                browse_button.setFixedSize(30, 30)
                browse_button.clicked.connect(partial(self.browse_for_file, file_path_edit))
                hbox.addWidget(file_path_edit);
                hbox.addWidget(browse_button)
                self.param_widgets[name] = file_path_edit
                self.param_form_layout.addRow(label_text, container)
                continue
            else:  # string, ip, port, etc.
                widget = QLineEdit()

            if widget:
                if spec.example: widget.setPlaceholderText(spec.example)
                if spec.type == "ip": widget.textChanged.connect(partial(self.validate_ip_input, widget))
                self.param_widgets[name] = widget
                self.param_form_layout.addRow(label_text, widget)

    def clear_param_form(self):
        """Безопасно очищает форму с параметрами."""
        self.form_execute_button.hide()
        self.param_widgets.clear()
        while self.param_form_layout.count():
            item = self.param_form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Рекурсивно очищаем вложенные layouts (для filepath)
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                item.layout().deleteLater()

    def browse_for_file(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать файл")
        if file_path: line_edit.setText(file_path)

    def validate_ip_input(self, widget, text):
        """Проверяет IP и устанавливает свойство для стилизации."""
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", text):
            widget.setProperty("validationState", "valid")
        else:
            widget.setProperty("validationState", "invalid")
        widget.style().unpolish(widget);
        widget.style().polish(widget)

    def execute_from_form(self):
        """Собирает параметры из формы, валидирует и запускает выполнение."""
        if not self.current_intent: return

        params, template = {}, self.command_templates.get_intent_template(self.current_intent)
        if not template: return

        for name, widget in self.param_widgets.items():
            value = ""
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
            elif isinstance(widget, QComboBox):
                text = widget.currentText()
                if spec_type := template.params[name].type:
                    if spec_type in ["choice_process", "choice_service"]:
                        value = text.split(' ')[0]  # Извлекаем только ID
                    else:
                        value = text
            if template.params[name].required and not value:
                QMessageBox.warning(self, "Ошибка ввода", f"Параметр '{name}' является обязательным.");
                return
            params[name] = value

        self.run_execution(self.current_intent, params)

    def execute_from_nlu(self):
        text = self.nlu_input.text().strip()
        if not text: return
        parsed = self.nlu_parser.parse(text)
        intent, params = parsed.get("intent"), parsed.get("params", {})

        if not intent:
            self.log_to_console("Команда не распознана.\n", "error");
            return

        template = self.command_templates.get_intent_template(intent)
        if not template: return

        # Проверяем, все ли обязательные параметры извлечены
        all_required_found = all(p_name in params for p_name, p_spec in template.params.items() if p_spec.required)

        if all_required_found:
            self.run_execution(intent, params)
        else:
            # Если не все параметры найдены, открываем форму для этой команды
            self.log_to_console(
                f"Команда '{template.description}' распознана. Пожалуйста, заполните недостающие параметры.\n", "info")
            # Находим и выбираем элемент в дереве
            it = QTreeWidgetItemIterator(self.function_tree, QTreeWidgetItemIterator.All)
            while it.value():
                item = it.value()
                if item.data(0, Qt.UserRole) == intent:
                    self.function_tree.setCurrentItem(item)
                    self.on_tree_item_clicked(item, 0)
                    # Заполняем уже найденные параметры
                    for name, value in params.items():
                        if name in self.param_widgets:
                            self.param_widgets[name].setText(value)
                    break
                it += 1

    def run_execution(self, intent: str, params: dict):
        if self.exec_thread and self.exec_thread.isRunning():
            self.log_to_console("! Предыдущая команда еще выполняется...\n", "warning");
            return

        self.output_console.clear()
        self.log_to_console(f"----- Запуск: {intent} -----\n", "header")
        masked_params = {k: '******' if 'password' in k else v for k, v in params.items()}
        self.log_to_console(f"> Параметры: {masked_params}\n", "info")
        self.logger.info(self.username, intent, params, "Execution started.")
        self.toggle_ui_for_execution(True)

        self.exec_thread = QThread()
        self.exec_worker = Worker(intent, params, self.command_templates)
        self.exec_worker.moveToThread(self.exec_thread)
        self.exec_worker.output.connect(self.handle_worker_output)
        self.exec_worker.finished.connect(self.on_execution_finished)
        self.exec_thread.started.connect(self.exec_worker.run)
        self.exec_thread.start()

    def on_execution_finished(self):
        self.log_to_console("\n----- Выполнение завершено -----\n", "success")
        self.toggle_ui_for_execution(False)
        if self.exec_thread:
            self.exec_thread.quit();
            self.exec_thread.wait()
            self.exec_thread, self.exec_worker = None, None

    def toggle_ui_for_execution(self, is_running: bool):
        self.form_execute_button.setEnabled(not is_running)
        self.function_tree.setEnabled(not is_running)
        self.nlu_input.setEnabled(not is_running)
        if is_running:
            self.spinner.start()
        else:
            self.spinner.stop()

    def handle_worker_output(self, text: str):
        if "ERROR:" in text:
            self.log_to_console(text, "error")
        else:
            self.log_to_console(text, "stdout")

    def log_to_console(self, text: str, msg_type: str = "stdout"):
        cursor = self.output_console.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        colors = {"stdout": "#dcddde", "header": "#7289da", "error": "#f04747", "warning": "#faa61a",
                  "success": "#43b581", "info": "#8e9297"}
        fmt.setForeground(QColor(colors.get(msg_type, "#dcddde")))
        if msg_type in ["header", "error", "success"]: fmt.setFontWeight(QFont.Bold)
        cursor.insertText(text, fmt)
        self.output_console.verticalScrollBar().setValue(self.output_console.verticalScrollBar().maximum())

    def closeEvent(self, event):
        if self.exec_thread and self.exec_thread.isRunning():
            self.exec_thread.quit();
            self.exec_thread.wait()
        self.logger.close();
        self.auth_manager.close()
        super().closeEvent(event)


def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    icon_path = icon.create_app_icon_if_not_exists()
    if icon_path and os.path.exists(icon_path): app.setWindowIcon(QIcon(icon_path))

    if os.name == 'nt':
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                QMessageBox.warning(None, "Требуются права администратора",
                                    "Для корректной работы некоторых команд рекомендуется перезапустить приложение от имени администратора.")
        except Exception as e:
            print(f"Не удалось проверить права администратора: {e}")

    try:
        auth_manager = AuthManager()
    except Exception as e:
        QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось инициализировать AuthManager: {e}");
        return

    login_dialog = LoginDialog(auth_manager)
    if login_dialog.exec_() == QDialog.Accepted:
        main_window = MainWindow(username=login_dialog.username, user_role=login_dialog.user_role,
                                 auth_manager=auth_manager)
        main_window.show()
        sys.exit(app.exec_())
    else:
        auth_manager.close();
        sys.exit(0)


if __name__ == "__main__":
    main()
