from django.db import models

class User(models.Model):
    user_roles = [
        ('guest', 'Гость'),
        ('speaker', 'Спикер')
    ]

    tg_id = models.IntegerField('Telegram ID')
    username = models.CharField(
        'Username', 
        max_length=255,
        blank=True
    )
    user_role = models.CharField(
        'Роль пользователя',
        max_length=255,
        choices=user_roles,
        default='guest'
    )
    name = models.CharField(
        'Имя', 
        max_length=255, 
        blank=True
    )
    company = models.CharField(
        'Компания',
        max_length=200,
        blank=True
    )
    position = models.CharField(
        'Должность',
        max_length=200,
        blank=True
    )
    about = models.TextField('О себе', blank=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username
    

class Event(models.Model):
    name = models.CharField('Название мероприятия', max_length=255)
    event_date = models.DateField('День мероприятия')
    started_at = models.TimeField('Время начала мероприятия')
    ended_at = models.TimeField('Время окончания мероприятия')

    class Meta:
        verbose_name = 'Мероприятие'
        verbose_name_plural = 'Мероприятия'

    def __str__(self):
        return self.name


class SpeakerSpeech(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        verbose_name='Мероприятие'
    )
    topic = models.CharField('Тема доклада', max_length=255)
    speaker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Спикер',
        limit_choices_to={'user_role': 'speaker'},
    )
    started_at = models.TimeField('Время начала выступления')
    ended_at = models.TimeField('Время окончания выступления')

    class Meta:
        verbose_name = 'Выступление спикера'
        verbose_name_plural = 'Выступления спикеров'

    def __str__(self):
        return self.topic


class Question(models.Model):
    speaker_speech = models.ForeignKey(
        SpeakerSpeech,
        on_delete=models.CASCADE,
        verbose_name='Выступление'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор вопроса'
    )
    text = models.TextField('Текст вопроса')
    created_at = models.DateTimeField('Время создания', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['created_at']
    
    def __str__(self):
        return f'Вопрос от {self.author.username} к {self.speaker_speech.topic[:30]}'
    

class Donation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        verbose_name='Мероприятие'
    )
    amount = models.DecimalField(
        'Сумма', 
        max_digits=10, 
        decimal_places=2
    )
    created_at = models.DateTimeField('Время доната', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Донат'
        verbose_name_plural = 'Донаты'
    
    def __str__(self):
        return f'{self.user.username} - {self.amount}₽'
    

class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Время создания подписки', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Подписка на следующие мероприятия'
        verbose_name_plural = 'Подписки на следующие мероприятия'
    
    def __str__(self):
        return f'{self.user.username} подписан'