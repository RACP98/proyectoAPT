from django.urls import path 
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
urlpatterns=[
    path('', views.index, name='index'), # Apuntar 127.0.0.1:8000/ a index.html
    # Cada una de mis paginas web:
    path('index',views.index, name='index'),
    path('perfil/', views.perfil, name='perfil'),
    path('registro', views.registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='finantrack/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('transacciones/<str:tipo>/', views.ver_transacciones, name='ver_transacciones'),

]
