from django.urls import path
from . import views

urlpatterns = [
    path('', views.interview_config, name='interview'),
    path('<int:interview_id>/submit/', views.submit_interview, name='submit_interview'),
    path('<int:interview_id>/result/', views.interview_result, name='interview_result'),
    path('<int:interview_id>/report/', views.interview_report, name='interview_report'),
    path('<int:interview_id>/delete/', views.delete_interview, name='delete_interview'),
    path('delete-all/', views.delete_all_interviews, name='delete_all_interviews'),
]
