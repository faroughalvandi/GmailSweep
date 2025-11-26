from django.contrib import admin
from django.urls import path
from cleaner import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),  
    path('dashboard/', views.dashboard, name='dashboard'),
    path('category/<str:category_key>/', views.preview_and_delete, name='delete_category'),
    path('logout/', views.logout_view, name='logout'),
]