import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup.settings')
django.setup()
from meetup_core.models import User, Event, SpeakerSpeech, Question
from asgiref.sync import sync_to_async
from telegram import Update 
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from dotenv import load_dotenv
from keyboards import (
    get_start_menu, get_user_menu, get_question_menu, 
    get_speaker_menu, get_speaker_active_menu, get_program_navigation
)
from datetime import datetime, time


WAITING_QUESTION = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    @sync_to_async
    def get_or_create_user():
        user_db, _ = User.objects.get_or_create(
            tg_id=user_id,
            defaults = {
                'username': user.username or '',
                'name': user.full_name or '',
                'user_role': 'guest'
            }
        )
        return user_db
    await get_or_create_user()
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


@sync_to_async
def get_events_from_db():
    """Получает мероприятия с выступлениями из БД"""
    events = Event.objects.prefetch_related(
        'speakerspeech_set__speaker'
    ).all().order_by('event_date')
    
    events_data = []
    for event in events:
        speeches = []
        for speech in event.speakerspeech_set.all().order_by('started_at'):
            speeches.append({
                'id': speech.id,
                'topic': speech.topic,
                'speaker': speech.speaker.name or speech.speaker.username,
                'started_at': speech.started_at,
                'ended_at': speech.ended_at
            })
        
        events_data.append({
            'id': event.id,
            'name': event.name,
            'event_date': event.event_date.strftime('%Y-%m-%d'),
            'started_at': event.started_at,
            'ended_at': event.ended_at,
            'speeches': speeches
        })
    
    return events_data


async def show_program(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=None):
    """Показывает текущее мероприятие в программе"""
    events = await get_events_from_db()
    current_index = context.user_data.get('current_event_index', 0)

    if not events:
        message = "Пока нет запланированных мероприятий"
        if edit_message:
            await edit_message.edit_text(message)
        else:
            await update.message.reply_text(message)
        return
    
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
    events = await get_events_from_db()

    if not events:
        await query.message.edit_text("Пока нет запланированных мероприятий")
        return

    current_index = context.user_data.get('current_event_index', 0)
    
    if callback_data.startswith("program_next"):
        current_index = (current_index + 1) % len(events)
    elif callback_data.startswith("program_prev"):
        current_index = (current_index - 1) % len(events)
    elif callback_data == "program_current":
        return
    
    context.user_data['current_event_index'] = current_index
    
    await show_program(update, context, edit_message=query.message)


async def get_current_speech():
    now = datetime.now()
    today_date = now.date()
    current_time = now.time()
    @sync_to_async
    def _get():
        event = Event.objects.filter(event_date=today_date).first()
        if not event:
            return None
        speech = SpeakerSpeech.objects.filter(
            event=event,
            started_at__lte=current_time,
            ended_at__gte=current_time
        ).select_related('speaker').first()
        return speech
    return await _get()


async def ask_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Задайте ваш вопрос спикеру.\n\nЧтобы отменить, нажмите Отмена.",
        reply_markup=get_question_menu()
    )
    return WAITING_QUESTION


async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_text = update.message.text
    tg_user = update.effective_user

    @sync_to_async
    def get_or_create_user():
        user, _ = User.objects.get_or_create(
            tg_id=tg_user.id,
            defaults = {
                'username': tg_user.username or '',
                'name': tg_user.full_name or '',
                'user_role': 'guest'
            }
        )
        return user
    user_db = await get_or_create_user()
    speech = await get_current_speech()
    if not speech:
        await update.message.reply_text(
            "Сейчас никто не выступает. Дождитесь, когда спикер начнет выступление",
            reply_markup = get_user_menu()
        )
        return ConversationHandler.END
    @sync_to_async
    def save_question():
        q = Question.objects.create(
            speaker_speech=speech,
            author=user_db,
            text=question_text
        )
        return q
    await save_question()
    
    speech = await get_current_speech()
    speaker = speech.speaker 
    if speaker.tg_id:
        try:
            await context.bot.send_message(
                chat_id=speaker.tg_id,
                text = f"Вопрос от {tg_user.full_name}\n\n{question_text}"
            )
        except Exception as e:
            print(f"Ошибка отправки вопроса спикеру: {e}")
    else:
        await update.message.reply_text("Спикер пока не настроен, но вопрос сохранен")
    await update.message.reply_text(
        "Ваш вопрос отправлен \n\nСпикер ответит после выступления",
        reply_markup=get_user_menu()
    )
    return ConversationHandler.END


async def cancel_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправка вопроса отменена",
        reply_markup=get_user_menu()
    )
    return ConversationHandler.END


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
    
    if event['speeches']:
        message += f"📋 *Программа выступлений:*\n"
        for i, speech in enumerate(event['speeches'], 1):
            message += f"\n{i}. {speech['topic']}\n"
            message += f"   👤 {speech['speaker']}\n"
            message += f"   🕐 {speech['started_at'].strftime('%H:%M')} - {speech['ended_at'].strftime('%H:%M')}\n"
    else:
        message += "📋 *Программа выступлений пока не объявлена*\n"
    
    return message


def main():
    load_dotenv()
    bot_token = os.getenv("TG_TOKEN")
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("speaker", toggle_speaker))
    question_hundler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^Задать вопрос$'), ask_question_start)
        ],
        states={
            WAITING_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question),
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex(r'^Отмена$'), cancel_question)
        ],
        allow_reentry=True
    )
    application.add_handler(question_hundler)
    application.add_handler(CallbackQueryHandler(handle_program_callback, pattern="^program_"))
    application.add_handler(MessageHandler(filters.TEXT, hundle_buttons))
    application.run_polling()


if __name__ == '__main__':
	main()