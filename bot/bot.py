import os
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, PreCheckoutQueryHandler
from dotenv import load_dotenv
from keyboards import get_start_menu, get_user_menu, get_question_menu, get_speaker_menu, get_speaker_active_menu

def start(update, context):
    user = update.effective_user
    user_id = user.id
    welcome_text = f"""Привет, {user.first_name}!
Я бот для митапов
С моей помощью вы сможете посмотреть программу мероприятия и задать вопрос ведущему, а так-же познакомиться с коллегами)))\n
Чтобы открыть меню нажми на кнопку 🏠 Меню """
    update.message.reply_text(welcome_text, reply_markup=get_start_menu())


def toggle_speaker(update, context):
    is_speaker = context.user_data.get('is_speaker', False)
    new_status = not is_speaker
    context.user_data['is_speaker'] = new_status
    if new_status:
        reply_text = "Поздравляем! Теперь вы спикер"
        reply_markup = get_speaker_menu()
    else:
        reply_text = "Вы больше не спикер"
        reply_markup = get_user_menu()
    update.message.reply_text(reply_text, reply_markup=reply_markup)


def show_program(update, context, reply_markup):
    update.message.reply_text("Тут будет программа мероприятия")

def ask_question(update, context):
    update.message.reply_text("Вы можете задать вопрос спикеру", reply_markup=get_question_menu())

def handle_speaker_buttons(update, context, reply_markup):
    text = update.message.text
    if text == "🏠 Меню":
        update.message.reply_text("🏠 Меню", reply_markup=reply_markup)
    if text == "Начать доклад":
        update.message.reply_text("Вы начали доклад", reply_markup=get_speaker_active_menu())
    if text == "Закончить доклад":
        update.message.reply_text("Вы закончили доклад", reply_markup=reply_markup)
    if text == "Вопросы от слушателей":
        update.message.reply_text("Тут будет список вопросов", reply_markup=get_question_menu())
    if text == "Программа":
        show_program(update, context, reply_markup)
    if text == "Режим слушателя":
        toggle_speaker(update, context)
    if text == "Отмена":
        update.message.reply_text("Вы вернулись в главное меню", reply_markup=get_speaker_active_menu())

def hundle_user_buttons(update, context, reply_markup):
    text = update.message.text
    if text == "🏠 Меню":
        update.message.reply_text("Вы в главном меню", reply_markup=reply_markup)
    if text == "Программа":
        show_program(update, context, reply_markup)
    if text == "Задать вопрос":
        ask_question(update, context)
    if text == "Текущий докладчик":
        update.message.reply_text("Отоброзится инфа о текущем докладчике", reply_markup=reply_markup)
    if text == "Поддержать проект":
        update.message.reply_text("Тут вы сможете поддержать проект", reply_markup=reply_markup)
    if text == "Курилка":
        update.message.reply_text("Тут вы сможете познакомиться с коллегами))")
    if text == "Отмена":
        update.message.reply_text("Вы вернулись в главное меню", reply_markup=reply_markup)

def hundle_buttons(update, context):
    if context.user_data.get('is_speaker', False):
        reply_markup = get_speaker_menu()
        handle_speaker_buttons(update, context, reply_markup)
    else:
        reply_markup = get_user_menu()
        hundle_user_buttons(update, context, reply_markup)


def main():
    load_dotenv()
    bot_token = os.getenv("TG_TOKEN")
    updater = Updater(bot_token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("speaker", toggle_speaker))
    dp.add_handler(MessageHandler(Filters.text, hundle_buttons))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
	main()