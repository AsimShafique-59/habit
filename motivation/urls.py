from django.urls import path

from .views import (
    AdminProgramDayDetailView,
    AdminProgramDayListCreateView,
    AdminProgramDetailView,
    AdminProgramListCreateView,
    CompleteDayView,
    EnrollmentListView,
    EnrollView,
    PersonalMediaListCreateView,
    ProgramDetailView,
    ProgramListView,
    QuitReasonDeleteView,
    QuitReasonListCreateView,
    SlipView,
    SOSActivateView,
    SOSUpdateView,
    TodayDayView,
    TriggerView,
)

urlpatterns = [
    path("motivation/programs/", ProgramListView.as_view()),
    path("motivation/programs/<slug:slug>/", ProgramDetailView.as_view()),
    path("motivation/enroll/", EnrollView.as_view()),
    path("motivation/enrollments/", EnrollmentListView.as_view()),
    path("motivation/enrollments/<uuid:pk>/today/", TodayDayView.as_view()),
    path("motivation/enrollments/<uuid:pk>/complete-day/", CompleteDayView.as_view()),
    path("motivation/enrollments/<uuid:pk>/slip/", SlipView.as_view()),
    path("motivation/enrollments/<uuid:pk>/triggers/", TriggerView.as_view()),
    path("motivation/enrollments/<uuid:pk>/sos/", SOSActivateView.as_view()),
    path("motivation/enrollments/<uuid:pk>/reasons/", QuitReasonListCreateView.as_view()),
    path("motivation/enrollments/<uuid:pk>/personal-media/", PersonalMediaListCreateView.as_view()),
    path("motivation/sos/<uuid:pk>/", SOSUpdateView.as_view()),
    path("motivation/reasons/<uuid:pk>/", QuitReasonDeleteView.as_view()),
    path("motivation/manage/programs/", AdminProgramListCreateView.as_view()),
    path("motivation/manage/programs/<slug:slug>/", AdminProgramDetailView.as_view()),
    path("motivation/manage/programs/<slug:slug>/days/", AdminProgramDayListCreateView.as_view()),
    path("motivation/manage/days/<uuid:pk>/", AdminProgramDayDetailView.as_view()),
]

