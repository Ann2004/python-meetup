from telegram import ReplyKeyboardMarkup, KeyboardButton

def get_start_menu():
	keyboard = [
	    [KeyboardButton("🏠 Меню")]
	]
	return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


#Меню пользователя(User)
def get_user_menu():
    keyboard = [
        [KeyboardButton("Программа"), KeyboardButton("Задать вопрос")],
        [KeyboardButton("Текущий докладчик"), KeyboardButton("Поддержать проект")],
        [KeyboardButton("Курилка")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


#Меню спикера(speaker)
def get_speaker_menu():
    keyboard = [
        [KeyboardButton("Начать доклад")],
        [KeyboardButton("Программа"), KeyboardButton("Режим слушателя")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

#Активное меню спикера
def get_speaker_active_menu():
	keyboard = [
	    [KeyboardButton("Закончить доклад")],
	    [KeyboardButton("Вопросы от слушателей")],
	    [KeyboardButton("🏠 Меню")]
	]
	return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

#Меню ввода вопроса
def get_question_menu():
    keyboard = [
        [KeyboardButton("Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
