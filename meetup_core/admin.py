from django.contrib import admin
from .models import (
    User, Event, SpeakerSpeech, Question, 
    Donation, Subscription, Broadcast
)
import asyncio
import os
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv
from asgiref.sync import sync_to_async
import threading


load_dotenv()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'user_role', 'company')
    list_filter = ('user_role',)
    search_fields = ('username', 'name', 'tg_id')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_date')
    list_filter = ('event_date',)
    search_fields = ('name',)


@admin.register(SpeakerSpeech)
class SpeakerSpeechAdmin(admin.ModelAdmin):
    list_display = ('topic', 'speaker', 'event', 'started_at', 'ended_at')
    list_filter = ('event',)
    search_fields = ('topic', 'speaker__name', 'speaker__username')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('author', 'speaker_speech', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'author__username')


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'amount', 'created_at')
    list_filter = ('event', 'created_at')
    search_fields = ('user__username',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('user__username',)


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'sent_at')
    readonly_fields = ('sent_at',)
    
    def text_preview(self, obj):
        """Превью текста для списка рассылок"""
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Текст сообщения'
    
    def save_model(self, request, obj, form, change):
        """Переопределение сохранения для отправки рассылки"""
        if not change:
            super().save_model(request, obj, form, change)
            thread = threading.Thread(
                target=self.send_broadcast_in_thread,
                args=(obj,)
            )
            thread.start()
        else:
            super().save_model(request, obj, form, change)
    
    def send_broadcast_in_thread(self, broadcast):
        """Запускает отправку рассылки в отдельном потоке"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                self._send_broadcast(broadcast)
            )
        finally:
            loop.close()
    
    async def _send_broadcast(self, broadcast):
        """Асинхронная отправка сообщений всем пользователям"""
        bot_token = os.getenv('TG_TOKEN')
        bot = Bot(token=bot_token)
        
        get_users = sync_to_async(list)(User.objects.all())
        users = await get_users
        
        for user in users:
            if user.tg_id:
                try:
                    await bot.send_message(
                        chat_id=user.tg_id,
                        text=broadcast.text,
                        parse_mode='HTML'
                    )
                except TelegramError as e:
                    print(f'Ошибка отправки пользователю {user.tg_id}: {e}')