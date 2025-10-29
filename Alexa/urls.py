from django.urls import path
from .views import AlexaChatAPIView, AnalyticsAPIView, ChatDataAPIView

urlpatterns = [
    path('', AlexaChatAPIView.as_view(), name='alexa_chat_api'),
    path('analytics/', AnalyticsAPIView.as_view(), name='analytics_api'),
    path('chat-data/', ChatDataAPIView.as_view(), name='chat_data_api'),
]
