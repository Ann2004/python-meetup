import os
from telegram import Update 
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
from keyboards import (
    get_start_menu, get_user_menu, get_question_menu, 
    get_speaker_menu, get_speaker_active_menu, get_program_navigation
)
from datetime import time


EVENTS = [ # заменить на данные из БД
    {
        'id': 1,
        'name': 'Митап по Python',
        'event_date': '2026-06-30',
        'started_at': time(10, 0),
        'ended_at': time(18, 0),
        'speeches': [
            {
                'topic': 'Тема доклада 1',
                'speaker': 'Алексей Петров',
                'started_at': time(10, 0),
                'ended_at': time(11, 30)
            },
            {
                'topic': 'Тема доклада 2',
                'speaker': 'Мария Иванова',
                'started_at': time(12, 0),
                'ended_at': time(13, 30)
            },
            {
                'topic': 'Тема доклада 3',
                'speaker': 'Дмитрий Сидоров',
                'started_at': time(14, 0),
                'ended_at': time(15, 30)
            }
        ]
    },
    {
        'id': 2,
        'name': 'Конференция по Data Science',
        'event_date': '2026-07-03',
        'started_at': time(9, 0),
        'ended_at': time(17, 0),
        'speeches': [
            {
                'topic': 'Тема доклада 1',
                'speaker': 'Анна Козлова',
                'started_at': time(9, 0),
                'ended_at': time(10, 30)
            },
            {
                'topic': 'Тема доклада 2',
                'speaker': 'Павел Морозов',
                'started_at': time(11, 0),
                'ended_at': time(12, 30)
            }
        ]
    },
    {
        'id': 3,
        'name': 'Web-разработка 2026',
        'event_date': '2026-07-05',
        'started_at': time(10, 0),
        'ended_at': time(16, 0),
        'speeches': [
            {
                'topic': 'Тема доклада 1',
                'speaker': 'Екатерина Волкова',
                'started_at': time(10, 0),
                'ended_at': time(11, 0)
            },
            {
                'topic': 'Тема доклада 2',
                'speaker': 'Игорь Соколов',
                'started_at': time(11, 30),
                'ended_at': time(13, 0)
            },
            {
                'topic': 'Тема доклада 3',
                'speaker': 'Ольга Медведева',
                'started_at': time(14, 0),
                'ended_at': time(15, 30)
            }
        ]
    }
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # Инициализируем индекс текущего мероприятия
    context.user_data['current_event_index'] = 0

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


async def show_program(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=None):
    """Показывает текущее мероприятие в программе"""
    events = EVENTS  # В будущем заменим на запрос к БД
    current_index = context.user_data.get('current_event_index', 0)
    
    if current_index >= len(events):
        current_index = 0
    elif current_index < 0:
        current_index = len(events) - 1
    
    context.user_data['current_event_index'] = current_index
    event = events[current_index]
    
    message = format_event_message(event)
    inline_keyboard = get_program_navigation(current_index, len(events))
    
    if edit_message:
        await edit_message.edit_text(
            message, 
            reply_markup=inline_keyboard,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message, 
            reply_markup=inline_keyboard,
            parse_mode='Markdown'
        )


async def handle_program_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов для навигации по программе"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    events = EVENTS
    current_index = context.user_data.get('current_event_index', 0)
    
    if callback_data.startswith("program_next"):
        current_index = (current_index + 1) % len(events)
    elif callback_data.startswith("program_prev"):
        current_index = (current_index - 1) % len(events)
    elif callback_data == "program_current":
        return
    
    context.user_data['current_event_index'] = current_index
    
    await show_program(update, context, edit_message=query.message)


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
        await show_program(update, context)
    elif text == "Режим слушателя":
        await toggle_speaker(update, context)
    elif text == "Отмена":
        await update.message.reply_text("Вы вернулись в главное меню", reply_markup=get_speaker_active_menu())


async def hundle_user_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_markup):
    text = update.message.text
    if text == "🏠 Меню":
        await update.message.reply_text("Вы в главном меню", reply_markup=reply_markup)
    elif text == "Программа":
        await show_program(update, context)
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


def format_event_message(event):
    """Форматирует сообщение с информацией о мероприятии"""
    message = f"*{event['name']}*\n"
    message += f"Дата: {event['event_date']}\n"
    message += f"Время: {event['started_at'].strftime('%H:%M')} - {event['ended_at'].strftime('%H:%M')}\n\n"
    message += f"📋 *Программа выступлений:*\n"
    
    for i, speech in enumerate(event['speeches'], 1):
        message += f"\n{i}. {speech['topic']}\n"
        message += f"   👤 {speech['speaker']}\n"
        message += f"   🕐 {speech['started_at'].strftime('%H:%M')} - {speech['ended_at'].strftime('%H:%M')}\n"
    
    return message


def main():
    load_dotenv()
    bot_token = os.getenv("TG_TOKEN")
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("speaker", toggle_speaker))
    application.add_handler(MessageHandler(filters.TEXT, hundle_buttons))
    application.add_handler(CallbackQueryHandler(handle_program_callback, pattern="^program_"))
    application.run_polling()


if __name__ == '__main__':
	main()