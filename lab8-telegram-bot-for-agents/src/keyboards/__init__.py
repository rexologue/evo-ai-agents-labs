from enum import Enum
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class Action(Enum):
    SELECT = "select"
    EDIT = "edit"
    DELETE = "delete"

# Главное меню
main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🆘 Помощь", callback_data="help"),
            InlineKeyboardButton(text="🚀 Начать работу", callback_data="start_work"),
        ]
    ]
)

# Меню помощи
help_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
    ]
)

# Меню начала работы
start_work_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔌 Подключиться к чату", callback_data="connect_to_chat")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
    ]
)

# Кнопка отмены подключения
connect_cancel_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить подключение", callback_data="cancel_connect")]
    ]
)

# Кнопка отключения от агента
disconnect_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔌 Отключиться от агента", callback_data="disconnect")]
    ]
)
