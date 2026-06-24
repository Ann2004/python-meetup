import os
from telegram import Update 
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from keyboards import (
    get_start_menu, get_user_menu, get_question_menu, 
    get_speaker_menu, get_speaker_active_menu
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    welcome_text = f"""Привет, {user.first_name}!
Я бот для митапов
С моей помощью вы сможете посмотреть программу мероприятия и задать вопрос ведущему, а так-же познакомиться с коллегами)))\n
Чтобы открыть меню нажми на кнопку 🏠 Меню """
    await update.message.reply_text(welcome_text, reply_markup=get_start_menu())


async def toggle_speaker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_speaker = context.user_data.get('is_speaker', False)
    new_status = not is_speaker
    context.user_data['is_speaker'] = new_status
    if new_status:
        reply_text = "Поздравляем! Теперь вы спикер"
        reply_markup = get_speaker_menu()
    else:
        reply_text = "Вы больше не спикер"
        reply_markup = get_user_menu()
    await update.message.reply_text(reply_text, reply_markup=reply_markup)


async def show_program(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_markup):
    await update.message.reply_text("Тут будет программа мероприятия", reply_markup=reply_markup)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вы можете задать вопрос спикеру", reply_markup=get_question_menu())

async def handle_speaker_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_markup):
    text = update.message.text
    if text == "🏠 Меню":
        await update.message.reply_text("🏠 Меню", reply_markup=reply_markup)
    elif text == "Начать доклад":
        await update.message.reply_text("Вы начали доклад", reply_markup=get_speaker_active_menu())
    elif text == "Закончить доклад":
        await update.message.reply_text("Вы закончили доклад", reply_markup=reply_markup)
    elif text == "Вопросы от слушателей":
        await update.message.reply_text("Тут будет список вопросов", reply_markup=get_question_menu())
    elif text == "Программа":
        await show_program(update, context, reply_markup)
    elif text == "Режим слушателя":
        await toggle_speaker(update, context)
    elif text == "Отмена":
        await update.message.reply_text("Вы вернулись в главное меню", reply_markup=get_speaker_active_menu())

async def hundle_user_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_markup):
    text = update.message.text
    if text == "🏠 Меню":
        await update.message.reply_text("Вы в главном меню", reply_markup=reply_markup)
    elif text == "Программа":
        await show_program(update, context, reply_markup)
    elif text == "Задать вопрос":
        await ask_question(update, context)
    elif text == "Текущий докладчик":
        await update.message.reply_text("Отобразится инфа о текущем докладчике", reply_markup=reply_markup)
    elif text == "Поддержать проект":
        await update.message.reply_text("Тут вы сможете поддержать проект", reply_markup=reply_markup)
    elif text == "Курилка":
        await update.message.reply_text("Тут вы сможете познакомиться с коллегами))")
    elif text == "Отмена":
        await update.message.reply_text("Вы вернулись в главное меню", reply_markup=reply_markup)

async def hundle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('is_speaker', False):
        reply_markup = get_speaker_menu()
        await handle_speaker_buttons(update, context, reply_markup)
    else:
        reply_markup = get_user_menu()
        await hundle_user_buttons(update, context, reply_markup)


def main():
    load_dotenv()
    bot_token = os.getenv("TG_TOKEN")
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("speaker", toggle_speaker))
    application.add_handler(MessageHandler(filters.TEXT, hundle_buttons))
    application.run_polling()


if __name__ == '__main__':
	main()