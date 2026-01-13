from django.urls import path
from .views import expense_list

urlpatterns = [
    path('', expense_list),
]