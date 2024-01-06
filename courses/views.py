import json
import logging

from typing import List, Optional
from urllib.parse import urlparse

from django.http import HttpRequest, HttpResponse

from django.contrib import messages
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Prefetch

from django.contrib.auth.decorators import login_required

from django.core.exceptions import ValidationError

from .models import (
    Course,
    Homework,
    Question,
    Answer,
    Submission,
    QuestionTypes,
    Enrollment,
)

from .scoring import is_free_form_answer_correct
from .forms import EnrollmentForm

logger = logging.getLogger(__name__)


NONE_LIST = [None]


def course_list(request):
    courses = Course.objects.all()
    return render(
        request, "courses/course_list.html", {"courses": courses}
    )


def course_detail(
    request: HttpRequest, course_slug: str
) -> HttpResponse:
    course = get_object_or_404(Course, slug=course_slug)

    user = request.user
    homeworks = get_homeworks_for_course(course, user)

    total_score = sum(hw.score or 0 for hw in homeworks)

    context = {
        "course": course,
        "homeworks": homeworks,
        "is_authenticated": user.is_authenticated,
        "total_score": total_score,
    }

    return render(request, "courses/course_detail.html", context)


def get_homeworks_for_course(course: Course, user) -> List[Homework]:
    if user.is_authenticated:
        queryset = Submission.objects.filter(student=user)
    else:
        queryset = Submission.objects.none()

    submissions_prefetch = Prefetch(
        "submission_set", queryset=queryset, to_attr="submissions"
    )

    homeworks = Homework.objects.filter(
        course=course
    ).prefetch_related(submissions_prefetch)

    for hw in homeworks:
        update_homework_with_additional_info(hw)

    return list(homeworks)


def update_homework_with_additional_info(homework: Homework) -> None:
    days_until_due = 0

    if homework.due_date > timezone.now():
        days_until_due = (homework.due_date - timezone.now()).days

    homework.days_until_due = days_until_due
    homework.submitted = False
    homework.score = None

    if not homework.submissions:
        return

    submission = homework.submissions[0]

    homework.submitted = True
    if homework.is_scored:
        homework.score = submission.total_score
    else:
        homework.submitted_at = submission.submitted_at


def process_quesion_free_form(
    homework: Homework, question: Question, answer: Answer
):
    if homework.is_scored:
        if not answer:
            return {"text": question.correct_answer}
        else:
            is_correct = is_free_form_answer_correct(
                user_answer=answer.answer_text,
                correct_answer=question.correct_answer,
                answer_type=question.answer_type,
            )

            if is_correct:
                correctly_selected = "option-answer-correct"
            else:
                correctly_selected = "option-answer-incorrect"

            return {
                "text": answer.answer_text,
                "correctly_selected_class": correctly_selected,
            }

    if not answer:
        return {"text": ""}
    else:
        return {"text": answer.answer_text}


def process_question_options_multiple_choice_or_checkboxes(
    homework: Homework, question: Question, answer: Optional[Answer]
):
    options = []

    if answer:
        answer_text = answer.answer_text or ""
        selected_options = answer_text.split(",")
    else:
        # no answer yet, so we need to show just options
        selected_options = []

    possible_answers = question.get_possible_answers()

    if homework.is_scored:
        correct_answers = (question.correct_answer or "").split(",")

    for option in possible_answers:
        is_selected = option in selected_options
        processed_answer = {
            "value": option,
            "is_selected": is_selected,
        }

        if homework.is_scored:
            is_correct = option in correct_answers

            correctly_selected = "option-answer-none"
            if is_selected and is_correct:
                correctly_selected = "option-answer-correct"
            if not is_selected and is_correct:
                correctly_selected = "option-answer-correct"
            if is_selected and not is_correct:
                correctly_selected = "option-answer-incorrect"

            processed_answer[
                "correctly_selected_class"
            ] = correctly_selected

        options.append(processed_answer)

    return {"options": options}


def process_question_options(
    homework: Homework, question: Question, answer: Answer
):
    if question.question_type == QuestionTypes.FREE_FORM.value:
        return process_quesion_free_form(homework, question, answer)

    return process_question_options_multiple_choice_or_checkboxes(
        homework, question, answer
    )


def tryparsefloat(value: str) -> Optional[float]:
    try:
        return float(value)
    except ValueError:
        return None


def clean_learning_in_public_links(
    links: List[str], cap: int
) -> List[str]:
    cleaned_links = []

    for link in links:
        if len(link) == 0:
            continue
        if link in cleaned_links:
            continue
        if len(cleaned_links) >= cap:
            break

        cleaned_links.append(link)

    return cleaned_links


def process_homework_submission(
    request: HttpRequest,
    course: Course,
    homework: Homework,
    questions: List[Question],
    submission: Optional[Submission],
):
    user = request.user

    answers_dict = {}
    for answer_id, answer in request.POST.lists():
        if not answer_id.startswith("answer_"):
            continue
        answers_dict[answer_id] = ",".join(answer)

    if submission:
        submission.submitted_at = timezone.now()
    else:
        enrollment, _ = Enrollment.objects.get_or_create(
            student=user,
            course=course,
        )
        submission = Submission.objects.create(
            homework=homework,
            student=user,
            enrollment=enrollment,
        )

    for question in questions:
        answer_text = answers_dict.get(f"answer_{question.id}")

        values = {"answer_text": answer_text, "student": user}

        Answer.objects.update_or_create(
            submission=submission,
            question=question,
            defaults=values,
        )

    if homework.homework_url_field:
        submission.homework_link = request.POST.get("homework_url")

    if homework.learning_in_public_cap > 0:
        links = request.POST.getlist("learning_in_public_links[]")
        cleaned_links = clean_learning_in_public_links(
            links, homework.learning_in_public_cap
        )
        submission.learning_in_public_links = cleaned_links

    if homework.time_spent_lectures_field:
        time_spent_lectures = request.POST.get("time_spent_lectures")
        if (
            time_spent_lectures is not None
            and time_spent_lectures != ""
        ):
            submission.time_spent_lectures = float(
                time_spent_lectures
            )

    if homework.time_spent_homework_field:
        time_spent_homework = request.POST.get("time_spent_homework")
        if (
            time_spent_homework is not None
            and time_spent_homework != ""
        ):
            submission.time_spent_homework = float(
                time_spent_homework
            )

    if homework.problems_comments_field:
        problem_comments = request.POST.get("problems_comments", "")
        submission.problems_comments = problem_comments.strip()

    if homework.faq_contribution_field:
        faq_contribution = request.POST.get("faq_contribution", "")
        submission.faq_contribution = faq_contribution.strip()

    submission.save()

    messages.success(
        request,
        "Thank you for submitting your homework, now your solution is saved. You can update it at any point.",
    )

    return redirect(
        "homework_detail",
        course_slug=course.slug,
        homework_slug=homework.slug,
    )


def homework_detail_build_context_not_authenticated(
    course: Course,
    homework: Homework,
    questions: List[Question],
) -> dict:
    question_answers = []
    for question in questions:
        options = process_question_options(homework, question, None)
        question_answers.append((question, options))

    context = {
        "course": course,
        "homework": homework,
        "question_answers": question_answers,
        "is_authenticated": False,
        "disabled": True,
    }

    return context


def homework_detail_build_context_authenticated(
    course: Course,
    homework: Homework,
    questions: List[Question],
    submission: Optional[Submission],
) -> dict:
    if submission:
        answers = Answer.objects.filter(
            submission=submission
        ).select_related("question")

        question_answers_map = {
            answer.question.id: answer for answer in answers
        }
    else:
        question_answers_map = {}

    # Pairing questions with their answers

    question_answers = []

    for question in questions:
        answer = question_answers_map.get(question.id)
        processed_answer = process_question_options(
            homework, question, answer
        )

        pair = (question, processed_answer)
        question_answers.append(pair)

    disabled = homework.is_scored

    context = {
        "course": course,
        "homework": homework,
        "question_answers": question_answers,
        "submission": submission,
        "is_authenticated": True,
        "disabled": disabled,
    }

    return context


def homework_detail(request: HttpRequest, course_slug: str, homework_slug: str):
    course = get_object_or_404(Course, slug=course_slug)

    homework = get_object_or_404(
        Homework, course=course, slug=homework_slug
    )
    questions = Question.objects.filter(homework=homework)

    user = request.user

    if not user.is_authenticated:
        context = homework_detail_build_context_not_authenticated(
            course=course, homework=homework, questions=questions
        )
        return render(
            request, "homework/homework_detail.html", context
        )

    submission = Submission.objects.filter(
        homework=homework, student=user
    ).first()

    # Process the form submission
    if request.method == "POST":
        return process_homework_submission(
            request=request,
            course=course,
            homework=homework,
            questions=questions,
            submission=submission,
        )

    context = homework_detail_build_context_authenticated(
        course=course,
        homework=homework,
        questions=questions,
        submission=submission,
    )

    return render(request, "homework/homework_detail.html", context)


def leaderboard_view(request, course_slug: str):
    course = get_object_or_404(Course, slug=course_slug)

    user = request.user
    enrollment_id = None

    if user.is_authenticated:
        enrollment = get_object_or_404(
            Enrollment, student=request.user, course__slug=course_slug
        )
        enrollment_id = enrollment.id

    enrollments = Enrollment.objects.filter(course=course).order_by(
        "-total_score"
    )

    context = {
        "enrollments": enrollments,
        "course": course,
        "current_student_enrollment_id": enrollment_id
    }

    return render(request, "courses/leaderboard.html", context)



def leaderboard_detail(request, course_slug: str, enrollment_id: int):
    # course = get_object_or_404(Course, slug=course_slug)
    # Get the specific enrollment
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, course__slug=course_slug)

    # Get submissions related to the enrollment
    submissions = Submission.objects.filter(enrollment=enrollment)

    context = {
        'enrollment': enrollment,
        'submissions': submissions,
    }

    return render(request, 'courses/leaderboard_detail.html', context)


@login_required
def enrollment_detail(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    enrollment = get_object_or_404(
        Enrollment, student=request.user, course__slug=course_slug
    )

    if request.method == "POST":
        form = EnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            form.save()
            # Redirect to a success page or show a success message
            return redirect("course_detail", course_slug=course_slug)

    form = EnrollmentForm(instance=enrollment)

    context = {
        "form": form,
        "course": course
    }

    return render(request, "courses/enrollment_detail.html", context)


