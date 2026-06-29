import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup.settings')
django.setup()
from meetup_core.models import User, Event, SpeakerSpeech, Question, Subscription, Donation
from asgiref.sync import sync_to_async
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler, PreCheckoutQueryHandler
from dotenv import load_dotenv
from keyboards import (
    get_start_menu, get_user_menu, get_question_menu, 
    get_speaker_menu, get_speaker_active_menu, get_program_navigation,
    get_networking_card_keyboard, get_donate_menu
)
from datetime import datetime, time
from random import choice
import time


WAITING_QUESTION = 1
ASK_NAME = 2
ASK_COMPANY = 3
ASK_POSITION = 4
ASK_ABOUT = 5


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


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    if "10⭐" in text:
        stars = 10
    elif "50⭐" in text:
        stars = 50
    elif "100⭐" in text:
        stars = 100
    else:
        return
    title = "Поддержка митапа"
    description = "Спасибо, что помогаете сообществу"
    payload = f"donation_{chat_id}_{int(time.time())}"
    prices = [LabeledPrice("Поддержка", stars)]
    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=prices,
            need_name=False,
            need_phone_number=False,
        )
    except Exception as e:
        await update.message.reply_text("Ошибка при создании счета")
        print(f"Ошибка:{e}")


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("donation_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Что-то пошло не так...")


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    total_amount = payment.total_amount
    user = update.effective_user

    @sync_to_async
    def save_donation():
        user_db, _ = User.objects.get_or_create(
            tg_id=user.id,
            defaults={
            'username': user.username or "",
            'name': user.full_name or "",
            'user_role': 'guest'
            }
        )
        Donation.objects.create(
            user=user_db,
            event=None,
            amount=total_amount
        )
    await save_donation()

    await update.message.reply_text(
        f"Спасибо за потдержку!\n"
        f"Вы отправили {total_amount} зыезд. Это поможет нам!"
    )


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

async def toggle_speaker(update:Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    @sync_to_async
    def change_role():
        user = User.objects.get(tg_id=user_id)
        if user.user_role == 'speaker':
            user.user_role = 'guest'
        else:
            user.user_role = 'speaker'
        user.save()
        return user.user_role
    new_role = await change_role()
    if new_role == 'guest':
        await update.message.reply_text("Вы стали слушателем)", reply_markup=get_user_menu())



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

async def get_active_speech():
    @sync_to_async
    def _get():
        active = SpeakerSpeech.objects.filter(is_active=True).select_related('speaker').first()
        if active:
            return active
    return await _get()

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
    active = await get_active_speech()
    if not active:
        await update.message.reply_text(
            "Нет активных выступлений. Попробуйте позже)"
            )
        return ConversationHandler.END
    else:
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
    speech = await get_active_speech()
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
    if speech.is_active:
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


async def activate_speech(update:Update, context: ContextTypes.DEFAULT_TYPE):
    speech = await get_current_speech()
    if not speech:
        await update.message.reply_text(
            "Нет выступления, которое вы можете начать"
        )
        return
    if speech.speaker.tg_id != update.effective_user.id:
        await update.message.reply_text(
            "Это не ваше выступление"
        )
        return
    @sync_to_async
    def activate():
        speech.is_active = True
        speech.save()
    await activate()
    await update.message.reply_text(
        "Вы начали доклад",
        reply_markup=get_speaker_active_menu()
    )

@sync_to_async
def deactivate_speech(update:Update, context: ContextTypes.DEFAULT_TYPE):
    speech = SpeakerSpeech.objects.filter(
        speaker__tg_id=update.effective_user.id,
        is_active=True
    ).first()
    if not speech:
        return None
    if speech:
        speech.is_active = False
        speech.save()
    return speech

async def get_questions(update:Update, context: ContextTypes.DEFAULT_TYPE):
    @sync_to_async
    def questions():
        return list(Question.objects.filter(
            speaker_speech__speaker__tg_id=update.effective_user.id
        ).order_by('created_at'))
    questions = await questions()
    if not questions:
        await update.message.reply_text(
            "У вас пока нет вопросов"
        )
        return
    @sync_to_async
    def create_question():
        text = "Вопросы к вашему выступлению:\n\n"
        for i, q in enumerate(questions, 1):
            text += f"{i}.{q.text}\n от {q.author.name or q.author.username}\n\n"
        return text
    text = await create_question()
    await update.message.reply_text(text)


async def networking_next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_networking_card(update, context)
    await query.message.delete()



async def show_networking_card(update:Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message:
        chat_id = update.message.chat_id
    elif update.callback_query:
        chat_id = update.callback_query.message.chat_id
    else:
        return

    @sync_to_async
    def get_other_users():
        others = User.objects.filter(has_questionnaire=True).exclude(tg_id=user_id)
        return list(others)

    others = await get_other_users()
    if not others:
        text = "Пока никто не заполнил анкету. Попробуйте позже!"
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_user_menu()
        )
        return

    person = choice(others)
    text = f"{person.name or 'Аноним'}\n"
    if person.company and person.company != '-':
        text += f"Компания:{person.company}\n"
    if person.position and person.position != '-':
        text += f"Должность:{person.position}\n"
    if person.about and person.about != '-':
        text += f"О себе:{person.about}\n"
    if person.username:
        text += f"username: @{person.username}\n"
    if person.tg_id:
        text += f"tg_id: {person.tg_id}"
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup = get_networking_card_keyboard()
    )

async def networking_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    @sync_to_async
    def get_user():
        return User.objects.filter(tg_id=user_id).first()
    user_db = await get_user()
    if not user_db:
        await update.message.reply_text(
            "Пользователь не найден. Напишите /start"
        )
        return ConversationHandler.END

    if not user_db.has_questionnaire:
        await update.message.reply_text(
            "Давайте заполним анкету.\nВведите ваше имя(никнейм):",
            reply_markup=get_question_menu()
        )
        return ASK_NAME
    else:
        await show_networking_card(update, context)
        return ConversationHandler.END


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text
    @sync_to_async
    def update_user():
        user = User.objects.get(tg_id=user_id)
        user.name = name
        user.save()
        return user
    await update_user()
    await update.message.reply_text(
        "Название вашей компании. Если нет, напишите '-'",
        reply_markup=get_question_menu()
    )
    return ASK_COMPANY


async def ask_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    company = update.message.text
    @sync_to_async
    def update_user():
        user = User.objects.get(tg_id=user_id)
        user.company = company
        user.save()
        return user
    await update_user()
    await update.message.reply_text(
        "Введите вашу должность. Если нет, напишите '-'",
        reply_markup=get_question_menu()
    )
    return ASK_POSITION


async def ask_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    position = update.message.text
    @sync_to_async
    def update_user():
        user = User.objects.get(tg_id=user_id)
        user.position = position
        user.save()
        return user
    await update_user()
    await update.message.reply_text(
        "Расскажите немного о себе (чем занимаетесь, интересы, что ищете на митапе):",
        reply_markup=get_question_menu()
    )
    return ASK_ABOUT


async def ask_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    about = update.message.text
    @sync_to_async
    def update_user():
        user = User.objects.get(tg_id=user_id)
        user.about = about
        user.has_questionnaire = True
        user.save()
        return user
    await update_user()
    await update.message.reply_text(
        "Анкета заполнена"
    )
    await show_networking_card(update, context)
    return ConversationHandler.END


async def cancel_networking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Заполнение анкеты отменено.",
        reply_markup=get_user_menu()
    )
    return ConversationHandler.END

async def get_user_role(tg_id):
    @sync_to_async
    def _get_role():
        user=User.objects.filter(tg_id=tg_id).first()
        if not user:
            return 'guest'
        return user.user_role
    return await _get_role()


async def get_active_speaker(update:Update, context: ContextTypes.DEFAULT_TYPE):
    speech = await get_active_speech()
    if not speech:
        await update.message.reply_text(
            "Нет активных спикеров. Попробуйте позже",
            reply_markup=get_user_menu()
        )
        return
    @sync_to_async
    def get_speaker():
        text = f"Выступает: {speech.speaker.name}\n\n"
        if speech.speaker.company:
            text += f"Компания:{speech.speaker.company}\n"
        if speech.speaker.position:
            text += f"Должность:{speech.speaker.position}\n"
        if speech.speaker.about:
            text += f"О себе:{speech.speaker.about}\n"
        if speech.speaker.username:
            text += f"username: @{speech.speaker.username}\n"
        if speech.speaker.tg_id:
            text += f"tg_id: {speech.speaker.tg_id}"
        return text
    text = await get_speaker()
    await update.message.reply_text(text, reply_markup=get_user_menu())


async def toggle_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    @sync_to_async
    def get_user():
        return User.objects.get(tg_id=user_id)
    user_db = await get_user()

    @sync_to_async
    def toggle():
        sub, created = Subscription.objects.get_or_create(
            user=user_db,
            defaults={'is_active': True}
        )
        if not created:
            sub.is_active = not sub.is_active
            sub.save()
        return sub
    sub = await toggle()
    if sub.is_active:
        await update.message.reply_text(
            "Вы подписались на уыедомления о новых мероприятиях!",
            reply_markup=get_user_menu()
        )
    else:
        await update.message.reply_text(
            "Вы отписались от уведомлений о новых мероприятиях",
            reply_markup=get_user_menu()
        )


async def handle_speaker_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_markup):
    text = update.message.text
    if text == "🏠 Меню":
        await update.message.reply_text("🏠 Меню", reply_markup=reply_markup)
    elif text == "Начать доклад":
        await activate_speech(update, context)
    elif text == "Закончить доклад":
        speech = await deactivate_speech(update, context)
        if speech:
            await update.message.reply_text(
                "Вы закончили доклад. Спасибо за участие",
                reply_markup=get_speaker_menu()
            )
        else: 
            await update.message.reply_text(
                "У вас нет активного доклада"
            )
    elif text == "Вопросы от слушателей":
        await get_questions(update, context)
    elif text == "Программа":
        await show_program(update, context)
    elif text == "Режим слушателя":
        await toggle_speaker(update, context)
    elif text == "Отмена":
        await update.message.reply_text("Вы вернулись в главное меню", reply_markup=get_speaker_active_menu())


async def hendle_user_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_markup):
    text = update.message.text
    if text == "🏠 Меню":
        await update.message.reply_text("Вы в главном меню", reply_markup=reply_markup)
    elif text == "Программа":
        await show_program(update, context)
    elif text == "Текущий докладчик":
        await get_active_speaker(update, context)
    elif text == "Поддержать проект":
        await update.message.reply_text("Вы можете поддержать проект", reply_markup=get_donate_menu())
    elif text == "Подписаться":
        await toggle_subscription(update, context)


async def hundle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    role = await get_user_role(tg_id)
    if role == 'speaker':
        reply_markup = get_speaker_menu()
        await handle_speaker_buttons(update, context, reply_markup)
    else:
        reply_markup = get_user_menu()
        await hendle_user_buttons(update, context, reply_markup)


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
    networking_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^Курилка$'), networking_start)
        ],
        states={
            ASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)
            ],
            ASK_COMPANY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_company)
            ],
            ASK_POSITION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_position)
            ],
            ASK_ABOUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_about)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex(r'^Отмена$'), cancel_networking)
        ],
        allow_reentry = True,
    )
    application.add_handler(MessageHandler(filters.Regex(r'^Поддержать \d+⭐$'), donate))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    application.add_handler(networking_handler)
    application.add_handler(CallbackQueryHandler(networking_next_callback, pattern = "^networking_next$"))
    application.add_handler(CallbackQueryHandler(handle_program_callback, pattern="^program_"))
    application.add_handler(MessageHandler(filters.TEXT, hundle_buttons))
    application.run_polling()


if __name__ == '__main__':
	main()