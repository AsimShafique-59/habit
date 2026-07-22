from django.urls import path

from .views import (
    AcceptSuggestionsView,
    CoachingReviewLatestView,
    CoachingReviewRespondView,
    CoachingReviewTriggerView,
    GenerateHabitsView,
    NLModificationView,
    OnboardingAnswersView,
    OnboardingQuestionsView,
)

urlpatterns = [
    path("ai/onboarding/questions/", OnboardingQuestionsView.as_view(), name="ai-onboarding-questions"),
    path("ai/onboarding/answers/", OnboardingAnswersView.as_view(), name="ai-onboarding-answers"),
    path("ai/habits/generate/", GenerateHabitsView.as_view(), name="ai-habits-generate"),
    path("ai/habits/accept/", AcceptSuggestionsView.as_view(), name="ai-habits-accept"),
    path("ai/coaching/reviews/latest/", CoachingReviewLatestView.as_view(), name="ai-coaching-latest"),
    path("ai/coaching/reviews/trigger/", CoachingReviewTriggerView.as_view(), name="ai-coaching-trigger"),
    path("ai/coaching/reviews/<uuid:review_id>/respond/", CoachingReviewRespondView.as_view(), name="ai-coaching-respond"),
    path("habits/<uuid:habit_id>/modify-nl/", NLModificationView.as_view(), name="habits-modify-nl"),
]

