import logging

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from courses.models import (
    Course,
    Homework,
    Question,
    Submission,
    Answer,
    User,
    QuestionTypes,
    AnswerTypes,
    Enrollment,
)

from courses.scoring import (
    HomeworkScoringStatus,
    score_homework_submissions,
)


from .util import join_possible_answers

logger = logging.getLogger(__name__)


def fetch_fresh(obj):
    return obj.__class__.objects.get(pk=obj.id)


class HomeworkScoringTestCase(TestCase):
    def create_answers_for_student(self, submission, answers):
        for question, answer_text in zip(self.questions, answers):
            Answer.objects.create(
                submission=submission,
                question=question,
                student=submission.student,
                answer_text=answer_text,
            )

    def setUp(self):
        # Set up the data for the test

        self.course = Course.objects.create(
            slug="test-course",
            title="Test Course",
            description="Test Course Description",
        )

        self.homework = Homework.objects.create(
            course=self.course,
            slug="test-homework",
            title="Test Homework",
            due_date=timezone.now() - timedelta(hours=1)
        )

        # Create questions
        
        q1 = Question.objects.create(
            homework=self.homework,
            text="What is the capital of France?",
            correct_answer="paris",
            question_type=QuestionTypes.FREE_FORM.value,
            answer_type=AnswerTypes.EXACT_STRING.value,
            scores_for_correct_answer=1,
        )
        q2 = Question.objects.create(
            homework=self.homework,
            text="What is 5 multiplied by 3?",
            correct_answer="15",
            question_type=QuestionTypes.FREE_FORM.value,
            answer_type=AnswerTypes.INTEGER.value,
            scores_for_correct_answer=10,
        )
        q3 = Question.objects.create(
            homework=self.homework,
            text="Which gas is most abundant in Earth's atmosphere?",
            correct_answer="nitrogen",
            question_type=QuestionTypes.FREE_FORM.value,
            answer_type=AnswerTypes.EXACT_STRING.value,
            scores_for_correct_answer=100,
        )
        q4 = Question.objects.create(
            homework=self.homework,
            text="Is the Earth flat? (yes/no)",
            possible_answers=join_possible_answers(["yes", "no"]),
            correct_answer="2",
            question_type=QuestionTypes.MULTIPLE_CHOICE.value,
            answer_type=AnswerTypes.EXACT_STRING.value,
            scores_for_correct_answer=1000,
        )
        q5 = Question.objects.create(
            homework=self.homework,
            text="Water boils at 100 degrees Celsius. (true/false)",
            correct_answer="1",
            possible_answers=join_possible_answers(["true", "false"]),
            question_type=QuestionTypes.MULTIPLE_CHOICE.value,
            answer_type=AnswerTypes.EXACT_STRING.value,
            scores_for_correct_answer=10000,
        )
        q6 = Question.objects.create(
            homework=self.homework,
            text="Select the prime numbers: 2, 4, 5, 7, 8",
            possible_answers=join_possible_answers(["2", "4", "5", "7", "8"]),
            correct_answer="1,3,4",
            question_type=QuestionTypes.CHECKBOXES.value,
            answer_type=AnswerTypes.EXACT_STRING.value,
            scores_for_correct_answer=100000,
        )

        self.questions = [q1, q2, q3, q4, q5, q6]

        self.student1 = User.objects.create_user(username="student1")
        self.enrollment1 = Enrollment.objects.create(
            course=self.course, student=self.student1
        )

        self.student2 = User.objects.create_user(username="student2")
        self.enrollment2 = Enrollment.objects.create(
            course=self.course,
            student=self.student2,
        )


    def test_homework_scoring(self):
        submission1 = Submission.objects.create(
            homework=self.homework,
            student=self.student1,
            enrollment=self.enrollment1,
        )

        submission2 = Submission.objects.create(
            homework=self.homework,
            student=self.student2,
            enrollment=self.enrollment2,
        )

        answers_student1 = [
            "paris",  # Correct
            "15",  # Correct
            "oxygen",  # Incorrect
            "no",  # Correct
            "false",  # Incorrect
            "2,5",  # Partially correct, but 0 score anyway
        ]

        expected_score1 = 1 + 10 + 0 + 1000 + 0 + 0

        # Answers for student 2 (different mix of correct and incorrect)
        answers_student2 = [
            "london",  # Incorrect
            "20",  # Incorrect
            "nitrogen",  # Correct
            "yes",  # Incorrect
            "true",  # Correct
            "2,5,7",  # Correct
        ]
        
        expected_score2 = 0 + 0 + 100 + 0 + 10000 + 100000

        self.create_answers_for_student(
            submission1, answers_student1
        )
        self.create_answers_for_student(
            submission2, answers_student2
        )

        status, message = score_homework_submissions(self.homework.id)

        self.assertEquals(status, HomeworkScoringStatus.OK)

        self.homework = fetch_fresh(self.homework)
        submission1 = fetch_fresh(submission1)
        submission2 = fetch_fresh(submission2)

        self.assertEquals(status, HomeworkScoringStatus.OK)
        self.assertEquals(self.homework.is_scored, True)

        self.assertEquals(submission1.total_score, expected_score1)
        self.assertEquals(submission1.questions_score, expected_score1)
        self.assertEquals(submission1.faq_score, 0)
        self.assertEquals(submission1.learning_in_public_score, 0)        

        self.assertEquals(submission2.total_score, expected_score2)
        self.assertEquals(submission2.questions_score, expected_score2)
        self.assertEquals(submission2.faq_score, 0)
        self.assertEquals(submission2.learning_in_public_score, 0)        

        self.enrollment1 = fetch_fresh(self.enrollment1)
        self.enrollment2 = fetch_fresh(self.enrollment2)

        self.assertEquals(self.enrollment1.total_score, expected_score1)
        self.assertEquals(self.enrollment2.total_score, expected_score2)

    def test_homework_scoring_extra_fields(self):
        submission1 = Submission.objects.create(
            homework=self.homework,
            student=self.student1,
            enrollment=self.enrollment1,
        )

        answers_student1 = [
            "berlin",  # Inorrect
            "15",  # Correct
            "oxygen",  # Incorrect
            "no",  # Correct
            "false",  # Incorrect
            "2,5",  # Partially correct
        ]
        
        self.create_answers_for_student(
            submission1, answers_student1
        )

        submission1.learning_in_public_links = [
            "https://www.linkedin.com/feed/update/urn:li:activity:7142541710064054272/",
            "https://www.linkedin.com/feed/update/urn:li:activity:7141024622870773763/",
            "https://twitter.com/Al_Grigor/status/1685940623012999168",
        ]
        submission1.faq_contribution = "some FAQ contribution"
        submission1.save()

        status, message = score_homework_submissions(self.homework.id)

        self.assertEquals(status, HomeworkScoringStatus.OK)

        self.homework = fetch_fresh(self.homework)
        submission1 = fetch_fresh(submission1)

        self.assertEquals(status, HomeworkScoringStatus.OK)
        self.assertEquals(self.homework.is_scored, True)

        questions_score = 0 + 10 + 0 + 1000 + 0 + 0
        faq_score = 1
        learning_in_public_score = 3
        total_score = questions_score + faq_score + learning_in_public_score

        self.assertEquals(submission1.questions_score, questions_score)
        self.assertEquals(submission1.faq_score, faq_score)
        self.assertEquals(submission1.learning_in_public_score, learning_in_public_score)
        self.assertEquals(submission1.total_score, total_score)

        self.enrollment1 = fetch_fresh(self.enrollment1)
        self.assertEquals(self.enrollment1.total_score, total_score)


