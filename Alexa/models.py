from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.FloatField()
    guide_steps = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100, blank=True, null=True)  # <--- new field

    # Step-by-step guide instructions for AI assistant
    guide_steps = ArrayField(
        base_field=models.TextField(),
        blank=True,
        default=list,
        help_text="Step-by-step instructions for using/installing the product"
    )

    def __str__(self) -> str:
        return self.name


class KnowledgeBase(models.Model):
    """
    Stores frequently asked questions and answers for the chatbot.
    """
    question = models.CharField(max_length=255, unique=True)
    answer = models.TextField()
    category = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self) -> str:
        return self.question


class ChatSession(models.Model):
    """
    Tracks individual chat sessions with unique session IDs and context.
    """
    session_id = models.CharField(max_length=100, unique=True)
    user_name = models.CharField(max_length=100, blank=True, null=True)
    last_product = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Stores the last product referenced in this session"
    )
    current_step = models.CharField(
        max_length=50,
        default='greeting',
        help_text="Current step in the chatbot conversation flow"
    )
    conversation_data = models.JSONField(
        blank=True,
        null=True,
        help_text="Stores temporary data for the conversation flow"
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"ChatSession {self.session_id}"


class ChatMessage(models.Model):
    """
    Represents a message sent by the user or bot in a session.
    """
    SENDER_CHOICES = [
        ('user', 'User'),
        ('bot', 'Bot')
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    response = models.TextField(blank=True, null=True, help_text="Bot's response to the message")
    intent = models.CharField(max_length=50, blank=True, null=True, help_text="Detected intent for the message")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.sender.capitalize()}: {self.message[:30]}"


class ChatLog(models.Model):
    """
    Logs chatbot intents and user interactions for analytics.
    """
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    intent = models.CharField(max_length=50)
    message = models.TextField()
    selected_panel = models.CharField(max_length=50, blank=True, null=True, help_text="Panel selected by user")
    purpose = models.CharField(max_length=100, blank=True, null=True, help_text="User's stated purpose for the panel")
    user_interests = models.JSONField(blank=True, null=True, help_text="Tracked user interests and preferences")
    suggested_products = models.JSONField(blank=True, null=True, help_text="Suggested related products (controllers, power supplies, etc.)")
    configuration_summary = models.TextField(blank=True, null=True, help_text="Final configuration summary when user saves")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.intent} - {self.message[:30]}"
