from django.contrib import admin
from .models import Product, KnowledgeBase, ChatSession, ChatMessage, ChatLog
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user_name', 'current_step', 'created_at', 'messages_count')
    list_filter = ('current_step', 'created_at')
    search_fields = ('session_id', 'user_name')
    readonly_fields = ('session_id', 'created_at')

    def messages_count(self, obj):
        return obj.messages.count()
    messages_count.short_description = 'Messages Count'

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(messages_count=Count('messages'))

class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'sender', 'message', 'intent', 'created_at')
    list_filter = ('sender', 'intent', 'created_at')
    search_fields = ('message', 'intent')
    readonly_fields = ('created_at',)

    # Add date filters
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        filter_param = request.GET.get('filter')
        if filter_param:
            now = timezone.now()
            if filter_param == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif filter_param == 'week':
                start_date = now - timedelta(days=7)
            elif filter_param == 'month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif filter_param == 'year':
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                return qs
            qs = qs.filter(created_at__gte=start_date)
        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['filter_options'] = [
            {'value': 'today', 'label': 'Today'},
            {'value': 'week', 'label': 'This Week'},
            {'value': 'month', 'label': 'This Month'},
            {'value': 'year', 'label': 'This Year'},
        ]
        return super().changelist_view(request, extra_context)

class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'intent', 'message', 'selected_panel', 'purpose', 'created_at')
    list_filter = ('intent', 'selected_panel', 'purpose', 'created_at')
    search_fields = ('message', 'intent', 'purpose')
    readonly_fields = ('created_at',)

    # Add date filters
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        filter_param = request.GET.get('filter')
        if filter_param:
            now = timezone.now()
            if filter_param == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif filter_param == 'week':
                start_date = now - timedelta(days=7)
            elif filter_param == 'month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif filter_param == 'year':
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                return qs
            qs = qs.filter(created_at__gte=start_date)
        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['filter_options'] = [
            {'value': 'today', 'label': 'Today'},
            {'value': 'week', 'label': 'This Week'},
            {'value': 'month', 'label': 'This Month'},
            {'value': 'year', 'label': 'This Year'},
        ]
        return super().changelist_view(request, extra_context)

admin.site.register(Product)
admin.site.register(KnowledgeBase)
admin.site.register(ChatSession, ChatSessionAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(ChatLog, ChatLogAdmin)
