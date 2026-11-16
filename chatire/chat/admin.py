from django.contrib import admin

from .models import ChatSession, ChatSessionMember, ChatSessionMessage


admin.site.register(ChatSession)
admin.site.register(ChatSessionMember)
admin.site.register(ChatSessionMessage)
