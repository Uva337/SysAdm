# app_new_ui.py
"""
Главный файл приложения SysAdmin Assistant с графическим интерфейсом на PyQt5.
Версия с кардинально переработанным UI/UX и полной реализацией функций.
"""
import sys
import os
import re
import json
import platform
import time
import datetime
from functools import partial
from typing import List, Dict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QLabel, QSplitter, QTreeWidget,
    QTreeWidgetItem, QFormLayout, QDialog, QDialogButtonBox, QMessageBox,
    QInputDialog, QComboBox, QStackedWidget, QListWidget, QListWidgetItem,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMenuBar, QAction, QMenu, QAbstractItemView, QTreeWidgetItemIterator,
    QGroupBox, QScrollArea
)
from PyQt5.QtCore import (
    Qt, QThread, QObject, pyqtSignal, QPropertyAnimation, QEasingCurve,
    pyqtProperty, QSize, QTimer, QRegularExpression
)
from PyQt5.QtGui import (
    QFont, QIcon, QColor, QTextCursor, QTextCharFormat, QRegularExpressionValidator
)

# --- Импорт компонентов ---
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from auth_rbac import AuthManager, Role
from command_templates import CommandTemplates, ParamSpec
from logging_audit import AuditLogger
from utils import AdvancedNLUParser
from sysadmin_actions import execute_intent, SPECIAL_HANDLERS
from macro_engine import MacroEngine
from plugin_api import PluginManager
import icon
from spinner import SpinnerWidget

# --- Константы ---
COMMANDS_FILE = "commands.json"
FAVORITES_FILE = "favorites.json"
APP_VERSION = "1.7.0"

# --- Стили ---
STYLESHEET = """
    /* Основной фон и цвета */
    QMainWindow, QDialog { background-color: #2f3136; }
    QWidget { color: #dcddde; font-family: "Segoe UI", "Cantarell", sans-serif; font-size: 10pt; }

    /* Навигационная панель слева */
    QListWidget#navigation_list { 
        background-color: #202225; 
        border: none;
        padding-top: 10px;
    }
    QListWidget#navigation_list::item {
        padding: 12px;
        border-radius: 5px;
        color: #b9bbbe;
    }
    QListWidget#navigation_list::item:hover { background-color: #3a3c43; }
    QListWidget#navigation_list::item:selected { 
        background-color: #40444b; 
        color: #ffffff;
        font-weight: bold;
    }

    /* Дерево команд */
    QTreeWidget {
        background-color: #2f3136; border: none; font-size: 10pt; outline: 0;
    }
    QTreeWidget::item { padding: 6px 8px; border-radius: 4px; }
    QTreeWidget::item:hover { background-color: #3a3c43; }
    QTreeWidget::item:selected { background-color: #40444b; color: #ffffff; }

    /* Поля ввода и комбобоксы */
    QLineEdit, QComboBox {
        background-color: #202225; border: 1px solid #202225;
        border-radius: 4px; padding: 8px; color: #dcddde;
    }
    QLineEdit:focus, QComboBox:focus { border-color: #5865f2; }
    QLineEdit[readOnly="true"] { background-color: #292b2f; }
    QLineEdit[validation_state="invalid"] { border: 1px solid #f04747; }
    QLineEdit[validation_state="valid"] { border: 1px solid #43b581; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView {
        background-color: #2f3136; border: 1px solid #40444b;
        selection-background-color: #40444b; outline: 0;
    }

    /* Кнопки */
    QPushButton {
        background-color: #4f545c; color: #ffffff;
        border: none; padding: 8px 12px; border-radius: 4px;
    }
    QPushButton:hover { background-color: #5d636b; }
    QPushButton#animated_button, QPushButton#file_browse_button {
        background-color: #5865f2; color: #ffffff;
        border: none; padding: 8px 16px; border-radius: 4px; font-weight: 500;
    }
    QPushButton#quick_launch_button {
        background-color: #4f545c;
        color: #ffffff;
        border: 1px solid #5d636b;
        padding: 15px;
        border-radius: 5px;
        text-align: left;
    }
    QPushButton#quick_launch_button:hover { background-color: #5d636b; }
    QPushButton#animated_button:hover { background-color: #4752c4; }
    QPushButton#animated_button:pressed { background-color: #3b45a0; }
    QPushButton#animated_button:disabled { background-color: #4f545c; color: #9a9c9e; }

    /* Вывод текста и таблицы */
    QTextEdit, QTableWidget {
        background-color: #202225; border: 1px solid #40444b;
        border-radius: 4px; color: #dcddde;
        font-family: "Consolas", "Courier New", monospace;
    }
    QTableWidget { gridline-color: #40444b; }
    QHeaderView::section { background-color: #202225; padding: 4px; border: 1px solid #40444b; font-weight: bold; }

    /* Разделители и скроллбары */
    QSplitter::handle { background-color: #202225; }
    QSplitter::handle:hover { background-color: #7289da; }
    QScrollBar:vertical { background: #2f3136; width: 10px; margin: 0; }
    QScrollBar::handle:vertical { background: #202225; min-height: 20px; border-radius: 5px; }

    /* Меню */
    QMenuBar { background-color: #2f3136; color: #dcddde; }
    QMenuBar::item:selected { background-color: #40444b; }
    QMenu { background-color: #2f3136; border: 1px solid #202225; }
    QMenu::item:selected { background-color: #40444b; }
    QGroupBox { font-size: 12pt; font-weight: bold; color: #ffffff; border: 1px solid #40444b; border-radius: 5px; margin-top: 10px;}
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
    QScrollArea { border: none; }
"""

# --- Иконки и переводы ---
CATEGORY_TRANSLATIONS = {
    "Network": "Сеть", "System": "Система", "Process": "Процессы",
    "Disk": "Диски", "Software": "Программы", "Users": "Пользователи",
    "Services": "Службы", "Logs": "Логи и Журналы", "Fs": "Файловая система",
    "Power": "Питание",
}

INTENT_ICONS = {
    'dashboard': 'go-home', 'commands': 'go-jump', 'macros': 'view-media-playlist',
    'network.get_ip_config': 'network-wired', 'network.ping': 'network-transmit-receive',
    'system.info': 'dialog-information', 'process.list': 'view-process-tree',
    'disk.usage': 'drive-harddisk', 'power.reboot': 'system-reboot',
    'power.shutdown': 'system-shutdown', 'chat': 'dialog-information'
}


# --- Вспомогательные классы и виджеты ---

class Worker(QObject):
    finished = pyqtSignal()
    output = pyqtSignal(dict)

    def __init__(self, intent, params, command_templates):
        super().__init__()
        self.intent, self.params, self.command_templates = intent, params, command_templates

    def run(self):
        def emit_output(text):
            self.output.emit({"type": "stdout", "data": text})

        if self.intent in SPECIAL_HANDLERS:
            handler = SPECIAL_HANDLERS[self.intent]
            data = handler()
            self.output.emit({"type": self.intent, "data": data})
        else:
            execute_intent(self.intent, self.params, self.command_templates, emit_output)

        self.finished.emit()


class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("animated_button")
        self._color = QColor("#5865f2")
        self.hover_color = QColor("#4752c4")
        self.default_color = QColor("#5865f2")
        self.disabled_color = QColor("#4f545c")
        self.animation = QPropertyAnimation(self, b"buttonColor", self)
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.buttonColor = self.default_color

    def enterEvent(self, event):
        if self.isEnabled():
            self.animation.setEndValue(self.hover_color)
            self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.animation.setEndValue(self.default_color)
            self.animation.start()
        super().leaveEvent(event)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
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
    def __init__(self, auth_manager: AuthManager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.user_role = None
        self.username = ""
        self.setWindowTitle("Вход в SysAdmin Assistant")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)

        self.username_input.setPlaceholderText("Имя пользователя")
        self.password_input.setPlaceholderText("Пароль")

        form_layout.addRow("Пользователь:", self.username_input)
        form_layout.addRow("Пароль:", self.password_input)
        layout.addLayout(form_layout)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #f04747;")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.handle_login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.password_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        self.username = self.username_input.text().strip()
        password = self.password_input.text()
        if not self.username or not password:
            self.status_label.setText("Имя пользователя и пароль не могут быть пустыми.")
            return

        role = self.auth_manager.verify_user(self.username, password)
        if role:
            self.user_role = role
            self.accept()
        else:
            self.status_label.setText("Неверное имя пользователя или пароль.")


class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить нового пользователя")

        self.layout = QFormLayout(self)
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.role = QComboBox()
        self.role.addItems([r.value for r in Role])

        self.layout.addRow("Имя пользователя:", self.username)
        self.layout.addRow("Пароль:", self.password)
        self.layout.addRow("Роль:", self.role)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.layout.addRow(self.buttons)

    def get_data(self):
        return self.username.text(), self.password.text(), Role(self.role.currentText())


class UserManagementDialog(QDialog):
    def __init__(self, auth_manager: AuthManager, current_user: str, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.current_user = current_user
        self.setWindowTitle("Управление пользователями")
        self.setMinimumSize(500, 300)

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Имя пользователя", "Роль"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        pwd_btn = QPushButton("Сменить пароль")
        del_btn = QPushButton("Удалить")

        add_btn.clicked.connect(self.add_user)
        pwd_btn.clicked.connect(self.change_password)
        del_btn.clicked.connect(self.delete_user)

        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(pwd_btn)
        buttons_layout.addWidget(del_btn)
        layout.addWidget(self.table)
        layout.addLayout(buttons_layout)
        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(0)
        users = self.auth_manager.get_all_users()
        for i, user_data in enumerate(users):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(user_data["username"]))
            self.table.setItem(i, 1, QTableWidgetItem(user_data["role"]))

    def add_user(self):
        dialog = AddUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            username, password, role = dialog.get_data()
            if not username or not password:
                QMessageBox.warning(self, "Ошибка", "Имя и пароль не могут быть пустыми.")
                return
            if self.auth_manager.add_user(username, password, role):
                QMessageBox.information(self, "Успех", f"Пользователь '{username}' добавлен.")
                self.populate_table()
            else:
                QMessageBox.critical(self, "Ошибка", f"Пользователь '{username}' уже существует.")

    def change_password(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя.")
            return
        username = selected_items[0].text()
        new_password, ok = QInputDialog.getText(self, "Смена пароля", f"Введите новый пароль для '{username}':",
                                                QLineEdit.Password)
        if ok and new_password:
            if self.auth_manager.change_user_password(username, new_password):
                QMessageBox.information(self, "Успех", "Пароль изменен.")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось сменить пароль.")

    def delete_user(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя для удаления.")
            return
        username = selected_items[0].text()
        if username == self.current_user:
            QMessageBox.critical(self, "Ошибка", "Нельзя удалить самого себя.")
            return
        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить пользователя '{username}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.auth_manager.delete_user(username):
                QMessageBox.information(self, "Успех", f"Пользователь '{username}' удален.")
                self.populate_table()
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить пользователя '{username}'.")


class PluginManagementDialog(QDialog):
    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.setWindowTitle("Менеджер плагинов")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)
        self.plugin_list = QListWidget()
        layout.addWidget(self.plugin_list)

        btn_layout = QHBoxLayout()
        self.reload_btn = QPushButton("Перезагрузить")
        close_btn = QPushButton("Закрыть")
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.reload_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.reload_btn.clicked.connect(self.reload_plugins)
        close_btn.clicked.connect(self.accept)

        self.populate_list()

    def populate_list(self):
        self.plugin_list.clear()
        for plugin in self.plugin_manager.plugins:
            self.plugin_list.addItem(plugin.__class__.__name__)

    def reload_plugins(self):
        self.plugin_manager.reload_plugins()
        self.populate_list()


class InfoLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("font-size: 10pt; color: #b9bbbe; font-weight: bold;")


class ValueLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("font-size: 10pt; color: #ffffff;")


class MainWindow(QMainWindow):
    def __init__(self, username: str, user_role: Role, auth_manager: AuthManager):
        super().__init__()
        self.username, self.user_role, self.auth_manager = username, user_role, auth_manager
        self.command_templates = CommandTemplates()
        try:
            self.command_templates.load_from_json(COMMANDS_FILE)
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Не удалось загрузить '{COMMANDS_FILE}':\n{e}")
            sys.exit(1)

        self.nlu_parser = AdvancedNLUParser(self.command_templates)
        self.logger = AuditLogger()
        self.macro_engine = MacroEngine(self.run_execution_for_macro)
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()
        self.favorites = self.load_favorites()

        self.current_intent = None
        self.param_widgets = {}
        self.exec_thread, self.exec_worker = None, None

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"SysAdmin Assistant - [{self.username} - {self.user_role.value.upper()}]")
        self.setGeometry(100, 100, 1280, 800)
        self.init_menu()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        nav_list = QListWidget()
        nav_list.setObjectName("navigation_list")
        nav_list.setFixedWidth(180)
        nav_list.setIconSize(QSize(24, 24))
        main_layout.addWidget(nav_list)

        self.main_stack = QStackedWidget()
        main_layout.addWidget(self.main_stack)

        self.dashboard_page = self.create_dashboard_page()
        self.commands_page = self.create_commands_page()
        self.macros_page = self.create_macros_page()
        self.chat_page = self.create_chat_page()

        self.main_stack.addWidget(self.dashboard_page)
        self.main_stack.addWidget(self.commands_page)
        self.main_stack.addWidget(self.macros_page)
        self.main_stack.addWidget(self.chat_page)

        self.add_nav_item("Быстрый запуск", 'dashboard', nav_list)
        self.add_nav_item("Команды", 'commands', nav_list)
        self.add_nav_item("Макросы", 'macros', nav_list)
        self.add_nav_item("Чат", 'chat', nav_list)

        nav_list.currentRowChanged.connect(self.main_stack.setCurrentIndex)
        nav_list.setCurrentRow(0)

    def init_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Файл")
        exit_action = QAction(QIcon.fromTheme("application-exit"), "Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menu_bar.addMenu("Инструменты")
        plugins_action = QAction(QIcon.fromTheme("system-software-install"), "Менеджер плагинов", self)
        plugins_action.triggered.connect(self.open_plugin_manager)
        tools_menu.addAction(plugins_action)

        if self.user_role == Role.ADMIN:
            admin_menu = menu_bar.addMenu("Администрирование")
            user_mgm_action = QAction(QIcon.fromTheme("system-users"), "Управление пользователями", self)
            user_mgm_action.triggered.connect(self.open_user_management)
            admin_menu.addAction(user_mgm_action)

        help_menu = menu_bar.addMenu("Справка")
        about_action = QAction(QIcon.fromTheme("help-about"), "О программе", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def open_plugin_manager(self):
        dialog = PluginManagementDialog(self.plugin_manager, self)
        dialog.exec_()

    def open_user_management(self):
        dialog = UserManagementDialog(self.auth_manager, self.username, self)
        dialog.exec_()

    def show_about_dialog(self):
        QMessageBox.about(self, "О программе SysAdmin Assistant",
                          f"""
            <b>SysAdmin Assistant v{APP_VERSION}</b>
            <p>Ваш помощник для выполнения рутинных задач администрирования.</p>
            <p>Разработано для упрощения работы с командами в Windows и Linux.</p>
            """
                          )

    def add_nav_item(self, name, icon_key, list_widget):
        item = QListWidgetItem(QIcon.fromTheme(INTENT_ICONS.get(icon_key, 'application-x-executable')), name)
        item.setFont(QFont("Segoe UI", 11, QFont.Bold))
        item.setSizeHint(QSize(40, 40))
        list_widget.addItem(item)

    def create_dashboard_page(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Статическая информация
        info_group = QGroupBox("Информация о системе")
        info_layout = QFormLayout(info_group)
        info_layout.addRow(InfoLabel("Имя хоста:"), ValueLabel(platform.node()))
        info_layout.addRow(InfoLabel("Операционная система:"), ValueLabel(f"{platform.system()} {platform.release()}"))
        main_layout.addWidget(info_group)

        if PSUTIL_AVAILABLE:
            stats_group = QGroupBox("Загрузка системы")
            stats_layout = QFormLayout(stats_group)
            self.cpu_value = ValueLabel()
            self.mem_value = ValueLabel()
            stats_layout.addRow(InfoLabel("CPU:"), self.cpu_value)
            stats_layout.addRow(InfoLabel("Память:"), self.mem_value)
            main_layout.addWidget(stats_group)

            self.stats_timer = QTimer(self)
            self.stats_timer.timeout.connect(self.update_system_stats)
            self.stats_timer.start(1000)

        # Панель быстрого запуска
        self.quick_launch_group = QGroupBox("Панель быстрого запуска (Избранное)")
        self.quick_launch_layout = QGridLayout(self.quick_launch_group)
        self.populate_quick_launch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.quick_launch_group)

        main_layout.addWidget(scroll_area, 1)  # Растягиваем
        return page

    def populate_quick_launch(self):
        # Очищаем старые виджеты
        while self.quick_launch_layout.count():
            item = self.quick_launch_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Заполняем заново
        row, col = 0, 0
        intents_to_show = self.favorites
        if not intents_to_show:  # Если избранное пустое, показываем дефолтные
            intents_to_show = ["network.ping", "process.list", "disk.usage", "system.info", "network.get_ip_config",
                               "network.clear_dns_cache"]

        for intent in intents_to_show:
            template = self.command_templates.get_intent_template(intent)
            if not template: continue

            btn = QPushButton(f"{template.description}")
            btn.setIcon(QIcon.fromTheme(INTENT_ICONS.get(intent, 'go-jump')))
            btn.setObjectName("quick_launch_button")
            btn.clicked.connect(partial(self.handle_quick_launch, intent))

            self.quick_launch_layout.addWidget(btn, row, col)
            col += 1
            if col >= 3:  # 3 кнопки в ряду
                col = 0
                row += 1

    def handle_quick_launch(self, intent):
        # Переключаемся на вкладку "Команды"
        self.main_stack.setCurrentIndex(1)

        # Находим элемент в дереве
        iterator = QTreeWidgetItemIterator(self.function_tree)
        found_item = None
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.UserRole) == intent:
                found_item = item
                break
            iterator += 1

        if found_item:
            self.function_tree.setCurrentItem(found_item)
            self.on_tree_item_clicked(found_item, 0)
        else:
            self.log_to_console(f"Команда '{intent}' не найдена в дереве.", "error")

    def create_commands_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.command_search_input = QLineEdit()
        self.command_search_input.setPlaceholderText("Фильтр команд...")
        self.command_search_input.textChanged.connect(self.filter_command_tree)
        self.function_tree = QTreeWidget()
        self.function_tree.setHeaderHidden(True)
        self.function_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.function_tree.customContextMenuRequested.connect(self.show_tree_context_menu)

        left_layout.addWidget(self.command_search_input)
        left_layout.addWidget(self.function_tree)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 10, 15, 10)

        nlu_layout = QHBoxLayout()
        self.nlu_input = QLineEdit()
        self.nlu_input.setPlaceholderText("Введите команду на естественном языке...")
        self.spinner = SpinnerWidget()
        self.spinner.hide()
        nlu_layout.addWidget(self.nlu_input)
        nlu_layout.addWidget(self.spinner)

        self.param_form_widget = QWidget()
        self.param_form_layout = QFormLayout(self.param_form_widget)
        self.param_form_layout.setContentsMargins(0, 10, 0, 10)

        self.form_execute_button = AnimatedButton("Выполнить команду")
        self.form_execute_button.hide()

        self.output_stack = QStackedWidget()
        self.output_console = QTextEdit()
        self.output_console.setReadOnly(True)
        self.output_table = QTableWidget()
        self.output_stack.addWidget(self.output_console)
        self.output_stack.addWidget(self.output_table)

        right_layout.addLayout(nlu_layout)
        right_layout.addWidget(self.param_form_widget)
        right_layout.addWidget(self.form_execute_button)
        right_layout.addStretch(1)
        right_layout.addWidget(self.output_stack, 5)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])

        self.populate_function_tree()
        self.function_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.nlu_input.returnPressed.connect(self.execute_from_nlu)
        self.form_execute_button.clicked.connect(self.execute_from_form)
        return page

    def create_macros_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        controls_layout = QHBoxLayout()
        self.record_button = QPushButton("Начать запись")
        self.record_button.setIcon(QIcon.fromTheme('media-record'))
        self.record_button.setCheckable(True)
        self.record_button.toggled.connect(self.toggle_recording)

        save_btn = QPushButton("Сохранить макрос")
        save_btn.setIcon(QIcon.fromTheme('document-save'))
        load_btn = QPushButton("Загрузить макрос")
        load_btn.setIcon(QIcon.fromTheme('document-open'))
        play_btn = QPushButton("Воспроизвести")
        play_btn.setIcon(QIcon.fromTheme('media-playback-start'))

        controls_layout.addWidget(self.record_button)
        controls_layout.addWidget(save_btn)
        controls_layout.addWidget(load_btn)
        controls_layout.addWidget(play_btn)

        self.macro_list_widget = QListWidget()
        layout.addLayout(controls_layout)
        layout.addWidget(self.macro_list_widget)

        save_btn.clicked.connect(self.save_macro)
        load_btn.clicked.connect(self.load_macro)
        play_btn.clicked.connect(lambda: self.macro_engine.play_macro(self.macro_engine.recorded_macro))
        return page

    def create_chat_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        send_btn = QPushButton("Отправить")
        send_btn.clicked.connect(self.handle_chat_send)
        input_layout.addWidget(self.chat_input, 1)
        input_layout.addWidget(send_btn)
        layout.addWidget(self.chat_history, 1)
        layout.addLayout(input_layout)
        return page

    def populate_function_tree(self):
        self.function_tree.clear()

        self.favorites_item = QTreeWidgetItem(self.function_tree, ["⭐ Избранное"])
        self.favorites_item.setFont(0, QFont("Segoe UI", 10, QFont.Bold))
        self.update_favorites_tree()

        categories = {}
        for intent, template in self.command_templates.intents.items():
            category_key = intent.split('.')[0].capitalize()
            if category_key not in categories: categories[category_key] = []
            categories[category_key].append(template)

        for category_key, templates in sorted(categories.items()):
            category_name = CATEGORY_TRANSLATIONS.get(category_key, category_key)
            category_item = QTreeWidgetItem(self.function_tree, [category_name])
            category_item.setFont(0, QFont("Segoe UI", 10, QFont.Bold))
            for template in sorted(templates, key=lambda t: t.description):
                child_item = QTreeWidgetItem(category_item, [template.description])
                child_item.setIcon(0, QIcon.fromTheme(INTENT_ICONS.get(template.intent, 'application-x-executable')))
                child_item.setData(0, Qt.UserRole, template.intent)
                child_item.setToolTip(0, f"Интент: {template.intent}")

    def update_favorites_tree(self):
        for i in reversed(range(self.favorites_item.childCount())):
            self.favorites_item.takeChild(i)

        for intent in sorted(self.favorites):
            template = self.command_templates.get_intent_template(intent)
            if template:
                child = QTreeWidgetItem(self.favorites_item, [template.description])
                child.setData(0, Qt.UserRole, intent)
                child.setIcon(0, QIcon.fromTheme(INTENT_ICONS.get(intent, 'emblem-favorite')))
        self.favorites_item.setExpanded(True)

    def _filter_recursive(self, item: QTreeWidgetItem, text: str) -> bool:
        item_text_matches = text in item.text(0).lower() or text in item.toolTip(0).lower()
        if item.childCount() == 0:
            item.setHidden(not item_text_matches)
            return item_text_matches
        else:
            child_matches = False
            for i in range(item.childCount()):
                if self._filter_recursive(item.child(i), text):
                    child_matches = True
            item.setHidden(not child_matches)
            return child_matches

    def filter_command_tree(self, text: str):
        text = text.lower()
        for i in range(self.function_tree.topLevelItemCount()):
            self._filter_recursive(self.function_tree.topLevelItem(i), text)

    def show_tree_context_menu(self, position):
        item = self.function_tree.itemAt(position)
        if not item or not item.data(0, Qt.UserRole): return
        intent = item.data(0, Qt.UserRole)
        menu = QMenu()
        action_text = "Удалить из избранного" if intent in self.favorites else "Добавить в избранное"
        action = QAction(action_text, self)
        action.triggered.connect(lambda: self.toggle_favorite(intent))
        menu.addAction(action)
        menu.exec_(self.function_tree.mapToGlobal(position))

    def toggle_favorite(self, intent):
        if intent in self.favorites:
            self.favorites.remove(intent)
        else:
            self.favorites.append(intent)
        self.save_favorites()
        self.update_favorites_tree()
        self.populate_quick_launch()  # Обновляем панель быстрого запуска

    def on_tree_item_clicked(self, item, column):
        intent = item.data(0, Qt.UserRole)
        if not intent:
            self.clear_param_form()
            return
        template = self.command_templates.get_intent_template(intent)
        if not template: return
        self.clear_param_form()
        if not template.params:
            self.run_execution(intent, {})
        else:
            self.create_param_form(template)

    def create_param_form(self, template):
        self.current_intent = template.intent
        for name, spec in template.params.items():
            label = QLabel(f"{name.capitalize()}{' *' if spec.required else ''}:")
            widget = None
            if spec.type == "filepath":
                widget_layout = QHBoxLayout()
                line_edit = QLineEdit()
                browse_btn = QPushButton("...")
                browse_btn.setFixedSize(30, 30)
                browse_btn.setObjectName("file_browse_button")
                browse_btn.clicked.connect(partial(self.browse_for_file, line_edit))
                widget_layout.addWidget(line_edit)
                widget_layout.addWidget(browse_btn)
                widget = line_edit
                self.param_form_layout.addRow(label, widget_layout)
            else:
                if spec.type == "choice" and spec.choices:
                    widget = QComboBox()
                    widget.addItems(spec.choices)
                else:
                    widget = QLineEdit()
                if spec.type == "password":
                    widget.setEchoMode(QLineEdit.Password)
                if spec.type == "ip" or spec.type == "ip_mask":
                    widget.textChanged.connect(partial(self.validate_ip_input, widget))
                if spec.example: widget.setPlaceholderText(spec.example)
                self.param_form_layout.addRow(label, widget)
            if widget:
                widget.setToolTip(f"Параметр: {name}\nТип: {spec.type}")
                self.param_widgets[name] = widget
        self.form_execute_button.show()

    def clear_param_form(self):
        self.form_execute_button.hide()
        self.current_intent = None
        self.param_widgets.clear()
        while self.param_form_layout.count():
            item = self.param_form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                item.layout().deleteLater()

    def browse_for_file(self, line_edit_widget):
        filename, _ = QFileDialog.getOpenFileName(self, "Выберите файл")
        if filename:
            line_edit_widget.setText(filename)

    def validate_ip_input(self, widget, text):
        ip_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        if re.match(ip_pattern, text):
            widget.setProperty("validation_state", "valid")
        else:
            widget.setProperty("validation_state", "invalid")
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def execute_from_nlu(self):
        text = self.nlu_input.text().strip()
        if not text: return
        parsed = self.nlu_parser.parse(text)
        intent, params = parsed.get("intent"), parsed.get("params", {})
        if not intent:
            self.log_to_console("Команда не распознана.\n", "error")
            return

        template = self.command_templates.get_intent_template(intent)
        if not template:
            self.log_to_console(f"Ошибка: найден интент '{intent}', но нет шаблона.\n", "error")
            return

        missing_required = False
        for p_name, p_spec in template.params.items():
            if p_spec.required and p_name not in params:
                missing_required = True
                break

        if not missing_required:
            self.log_to_console("Все обязательные параметры распознаны, выполняю команду...\n", "success")
            self.run_execution(intent, params)
        else:
            iterator = QTreeWidgetItemIterator(self.function_tree)
            found = False
            while iterator.value():
                item = iterator.value()
                if item.data(0, Qt.UserRole) == intent:
                    self.function_tree.setCurrentItem(item)
                    self.function_tree.scrollToItem(item)
                    found = True
                    break
                iterator += 1
            if not found:
                self.log_to_console(f"Интент '{intent}' найден, но отсутствует в дереве.\n", "error")
                return

            self.clear_param_form()
            self.create_param_form(template)

            for name, widget in self.param_widgets.items():
                if name in params:
                    if isinstance(widget, QComboBox):
                        index = widget.findText(params[name], Qt.MatchFixedString)
                        if index >= 0: widget.setCurrentIndex(index)
                    else:
                        widget.setText(str(params[name]))
            self.log_to_console(f"Распознана команда '{template.description}'. Заполните недостающие параметры.\n",
                                "info")

    def execute_from_form(self):
        if not self.current_intent: return
        params, template = {}, self.command_templates.get_intent_template(self.current_intent)
        for name, widget in self.param_widgets.items():
            value = widget.text().strip() if isinstance(widget, QLineEdit) else widget.currentText()
            if value:
                params[name] = value
            elif template.params[name].required:
                QMessageBox.warning(self, "Ошибка ввода", f"Параметр '{name}' является обязательным.")
                return
        self.run_execution(self.current_intent, params)

    def run_execution(self, intent: str, params: dict):
        if self.exec_thread and self.exec_thread.isRunning():
            self.log_to_console("! Предыдущая команда еще выполняется...\n", "warning")
            return

        self.output_console.clear()
        self.output_table.clear()
        self.output_table.setRowCount(0)
        self.output_table.setColumnCount(0)

        self.log_to_console(f"----- Запуск: {intent} -----\n", "header")
        masked_params = {k: '******' if 'password' in k.lower() else v for k, v in params.items()}
        self.log_to_console(f"> Параметры: {masked_params}\n", "info")

        if self.macro_engine.is_recording:
            self.macro_engine.record_action(intent, params)
            self.macro_list_widget.addItem(f"{intent}: {masked_params}")

        self.logger.info(self.username, intent, params, "Execution started.")
        self.toggle_ui_for_execution(True)

        self.exec_worker = Worker(intent, params, self.command_templates)
        self.exec_thread = QThread()
        self.exec_worker.moveToThread(self.exec_thread)
        self.exec_worker.output.connect(self.handle_worker_output)
        self.exec_worker.finished.connect(self.on_execution_finished)
        self.exec_thread.started.connect(self.exec_worker.run)
        self.exec_thread.start()

    def run_execution_for_macro(self, intent: str, params: dict):
        if self.exec_thread and self.exec_thread.isRunning():
            self.log_to_console("! Предыдущая команда еще выполняется... Пропуск шага макроса.\n", "warning")
            QApplication.processEvents()
            return

        self.output_console.clear()
        self.output_table.clear();
        self.output_table.setRowCount(0);
        self.output_table.setColumnCount(0)
        self.log_to_console(f"----- Макрос: {intent} -----\n", "header")

        self.logger.info(self.username, f"MACRO: {intent}", params, "Execution started.")
        self.toggle_ui_for_execution(True)

        self.exec_worker = Worker(intent, params, self.command_templates)
        self.exec_thread = QThread()
        self.exec_worker.moveToThread(self.exec_thread)
        self.exec_worker.output.connect(self.handle_worker_output)
        self.exec_worker.finished.connect(self.on_execution_finished)
        self.exec_thread.started.connect(self.exec_worker.run)
        self.exec_thread.start()
        self.exec_thread.wait()

    def handle_worker_output(self, result: dict):
        output_type = result.get("type")
        data = result.get("data")

        parsers = {
            "process.list": self.parse_psutil_process_list,
            "disk.usage": self.parse_psutil_disk_usage,
            "disk.list": self.parse_psutil_disk_list,
        }

        if output_type in parsers:
            self.output_stack.setCurrentWidget(self.output_table)
            parsers[output_type](data)
        elif output_type == "stdout":
            self.output_stack.setCurrentWidget(self.output_console)
            if "ERROR:" in data:
                self.log_to_console(data, "error")
            else:
                self.log_to_console(data, "stdout")
        else:
            self.output_stack.setCurrentWidget(self.output_console)
            self.log_to_console(str(data), "stdout")

    def on_execution_finished(self):
        self.log_to_console("\n----- Выполнение завершено -----\n", "success")
        self.toggle_ui_for_execution(False)
        if self.exec_thread:
            if self.exec_thread.isRunning():
                self.exec_thread.quit()
                self.exec_thread.wait()
            self.exec_thread.deleteLater()
            self.exec_worker.deleteLater()
            self.exec_thread, self.exec_worker = None, None

    def toggle_ui_for_execution(self, is_running: bool):
        self.form_execute_button.setEnabled(not is_running)
        self.function_tree.setEnabled(not is_running)
        self.nlu_input.setEnabled(not is_running)
        if is_running:
            self.spinner.start()
        else:
            self.spinner.stop()

    def log_to_console(self, text: str, msg_type: str = "stdout"):
        self.output_stack.setCurrentWidget(self.output_console)
        cursor = self.output_console.textCursor()
        cursor.movePosition(QTextCursor.End)
        char_format = QTextCharFormat()
        colors = {"stdout": "#dcddde", "header": "#7289da", "error": "#f04747",
                  "warning": "#faa61a", "success": "#43b581", "info": "#8e9297"}
        char_format.setForeground(QColor(colors.get(msg_type, "#dcddde")))
        if msg_type in ["header", "error"]:
            char_format.setFontWeight(QFont.Bold)
        else:
            char_format.setFontWeight(QFont.Normal)
        cursor.insertText(text, char_format)
        self.output_console.verticalScrollBar().setValue(self.output_console.verticalScrollBar().maximum())

    def parse_psutil_process_list(self, data: str):
        lines = data.strip().split('\n')
        if len(lines) < 2: return
        headers = [h.strip() for h in re.split(r'\s{2,}', lines[0]) if h]
        self.output_table.setColumnCount(len(headers))
        self.output_table.setHorizontalHeaderLabels(headers)

        for i, line in enumerate(lines[2:]):
            self.output_table.insertRow(i)
            row_data = [d.strip() for d in re.split(r'\s{2,}', line.strip()) if d]
            for j, cell in enumerate(row_data):
                if j < self.output_table.columnCount():
                    self.output_table.setItem(i, j, QTableWidgetItem(cell))
        self.output_table.resizeColumnsToContents()

    def parse_psutil_disk_usage(self, data: str):
        lines = data.strip().split('\n')
        if len(lines) < 2: return
        headers = [h.strip() for h in re.split(r'\s{2,}', lines[0]) if h]
        self.output_table.setColumnCount(len(headers))
        self.output_table.setHorizontalHeaderLabels(headers)

        for i, line in enumerate(lines[2:]):
            self.output_table.insertRow(i)
            row_data = [d.strip() for d in re.split(r'\s{2,}', line.strip()) if d]
            for j, cell in enumerate(row_data):
                if j < self.output_table.columnCount():
                    self.output_table.setItem(i, j, QTableWidgetItem(cell))
        self.output_table.resizeColumnsToContents()

    def parse_psutil_disk_list(self, data: str):
        lines = data.strip().split('\n')
        if len(lines) < 2: return
        headers = [h.strip() for h in re.split(r'\s{2,}', lines[0]) if h]
        self.output_table.setColumnCount(len(headers))
        self.output_table.setHorizontalHeaderLabels(headers)
        for i, line in enumerate(lines[2:]):
            self.output_table.insertRow(i)
            row_data = [d.strip() for d in re.split(r'\s{2,}', line.strip()) if d]
            for j, cell in enumerate(row_data):
                if j < self.output_table.columnCount():
                    self.output_table.setItem(i, j, QTableWidgetItem(cell))
        self.output_table.resizeColumnsToContents()

    def toggle_recording(self, checked):
        if checked:
            self.macro_engine.start_recording()
            self.record_button.setText("Остановить запись")
            self.record_button.setIcon(QIcon.fromTheme('media-playback-stop'))
            self.macro_list_widget.clear()
        else:
            self.macro_engine.stop_recording()
            self.record_button.setText("Начать запись")
            self.record_button.setIcon(QIcon.fromTheme('media-record'))
            QMessageBox.information(self, "Запись завершена",
                                    f"Записано {len(self.macro_engine.recorded_macro)} действий.")

    def save_macro(self):
        if not self.macro_engine.recorded_macro:
            QMessageBox.warning(self, "Ошибка", "Нет записанных действий для сохранения.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить макрос", "", "JSON Files (*.json)")
        if path:
            self.macro_engine.save_macro_to_file(path)

    def load_macro(self):
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить макрос", "", "JSON Files (*.json)")
        if path:
            try:
                loaded_macro = self.macro_engine.load_macro_from_file(path)
                self.macro_engine.recorded_macro = loaded_macro
                self.macro_list_widget.clear()
                for action in loaded_macro:
                    self.macro_list_widget.addItem(f"{action['intent']}: {action['params']}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось загрузить макрос: {e}")

    def handle_chat_send(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_history.append(f"Вы: {text}")
        # Простейший ответ-заглушка
        self.chat_history.append(f"Bot: Я получил '{text}'")
        self.chat_input.clear()

    def update_system_stats(self):
        if not PSUTIL_AVAILABLE:
            return
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        self.cpu_value.setText(f"{cpu}%")
        self.mem_value.setText(f"{mem.percent}%")

    def load_favorites(self):
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save_favorites(self):
        try:
            with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=4)
        except IOError as e:
            print(f"Could not save favorites: {e}")

    def closeEvent(self, event):
        self.save_favorites()
        if self.exec_thread and self.exec_thread.isRunning():
            self.exec_thread.quit()
            self.exec_thread.wait()

        if hasattr(self, 'stats_timer'):
            self.stats_timer.stop()

        # if self.log_viewer_timer:
        #     self.log_viewer_timer.stop()
        # if self.log_viewer_thread and self.log_viewer_thread.isRunning():
        #     self.log_viewer_thread.quit()
        #     self.log_viewer_thread.wait()

        self.logger.close()
        self.auth_manager.close()
        super().closeEvent(event)


def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    icon_path = icon.create_app_icon_if_not_exists()
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    if os.name == 'nt':
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                QMessageBox.warning(None, "Требуются права администратора",
                                    "Для корректной работы некоторых команд рекомендуется перезапустить приложение от имени администратора.")
        except Exception as e:
            print(f"Could not check for admin rights: {e}")

    try:
        auth_manager = AuthManager()
    except Exception as e:
        QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось инициализировать AuthManager: {e}")
        return

    login_dialog = LoginDialog(auth_manager)
    if login_dialog.exec_() == QDialog.Accepted:
        main_window = MainWindow(username=login_dialog.username, user_role=login_dialog.user_role,
                                 auth_manager=auth_manager)
        main_window.show()
        sys.exit(app.exec_())
    else:
        auth_manager.close()
        sys.exit(0)


if __name__ == "__main__":
    import socket

    main()
