from asgiref.sync import async_to_sync
import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Event, Subscription
from telegram import Bot
from dotenv import load_dotenv



load_dotenv()
bot_token = os.getenv('TG_TOKEN')
bot = Bot(token=bot_token)


@receiver(post_save, sender=Event)
def notify_subscribers(sender, instance, created, **kwargs):
    if created:
        subscribers = Subscription.objects.filter(is_active=True).select_related('user')
        if not subscribers:
            return
        message = (
            f"*Новое мероприятие:*{instance.name}\n\n"
            f"Дата: {instance.event_date}\n"
            f"Время:{instance.started_at.strftime('%H:%M')}-{instance.ended_at.strftime('%H:%M')}\n"
        )
        for sub in subscribers:
            try:
                async_to_sync(bot.send_message)(chat_id=sub.user.tg_id, text=message, parse_mode='Markdown')
            except Exception as e:
                print(f"Ошибка при отправке уведомления пользователю.{sub.user.tg_id}: {e}")



