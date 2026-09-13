from django.urls import path

from .views import LoginView, LogoutView, PinResetConfirmView, PinResetRequestView, RegisterView, UserListView, UserMeView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('pin-reset/request/', PinResetRequestView.as_view(), name='pin-reset-request'),
    path('pin-reset/confirm/', PinResetConfirmView.as_view(), name='pin-reset-confirm'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('me/', UserMeView.as_view(), name='user-me'),
    path('', UserListView.as_view(), name='user-list'),
]
