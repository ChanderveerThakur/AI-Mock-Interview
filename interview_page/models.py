from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Interview(models.Model):

    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium','Medium'),
        ('hard', 'Hard'),
    ]

    TYPE_CHOICES = [
        ('mcq','MCQ'),
        ('text','Text'),
        ('mixed','Mixed'),
    ]

    user = models.ForeignKey(
        User, on_delete= models.CASCADE
    )

    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES
    )

    total_questions = models.IntegerField()

    experience = models.IntegerField()

    skills = models.TextField()

    interview_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(
        auto_now_add=True
    )


class Question(models.Model):

    QUESTION_TYPES = [
        ('mcq', 'MCQ'),
        ('text', 'Text'),
    ]

    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    question_text = models.TextField()

    question_type = models.CharField(
        max_length=10,
        choices=QUESTION_TYPES
    )

    options = models.JSONField(
        null=True,
        blank=True
    )

    correct_answer = models.TextField()

    expected_answer = models.TextField(
        null=True,
        blank=True
    )

    question_number = models.IntegerField()


class Answer(models.Model):

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    answer = models.TextField()

    score = models.IntegerField(
        null=True,
        blank=True
    )

    is_correct = models.BooleanField(
        null=True,
        blank=True
    )

    feedback = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )