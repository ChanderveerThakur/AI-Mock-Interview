import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .llm import get_gemini_response
from .models import Interview, Question, Answer


@login_required
def interview_config(request):

    if request.method == 'POST':

        difficulty = request.POST.get('difficulty', 'medium')
        total_questions = request.POST.get('total_questions', '5')
        experience = request.POST.get('experience', '1')
        skills = request.POST.get('skills', '')
        interview_type = request.POST.get('type', 'mixed')

        try:
            total_questions_int = int(total_questions)
            experience_int = int(experience)
        except ValueError:
            total_questions_int = 5
            experience_int = 1

        interview = Interview.objects.create(
            user=request.user,
            difficulty=difficulty,
            total_questions=total_questions_int,
            experience=experience_int,
            skills=skills,
            interview_type=interview_type
        )

        prompt = f"""
You are an AI technical interviewer.

Generate a mock technical interview based on:
Difficulty: {difficulty}
Total Questions: {total_questions_int}
Experience: {experience_int} years
Skills: {skills}
Type: {interview_type}

Rules:
- Questions must match the difficulty.
- Questions must match the candidate's experience.
- Questions must cover the specified skills.
- MCQ questions must have question_type="mcq", and options must be a JSON array of exactly 4 strings, with correct_answer matching one of the options.
- Text questions must have question_type="text", options=null, correct_answer="", and an expected_answer string.
- If Type is "mixed", mix both MCQ and Text questions. If Type is "mcq", only make MCQ. If Type is "text", only make Text.
- Return ONLY valid JSON as a list of question objects. Do not include extra commentary.

Format:
[
  {{
    "question_number": 1,
    "question_type": "mcq",
    "question_text": "What is ...?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "expected_answer": null
  }},
  {{
    "question_number": 2,
    "question_type": "text",
    "question_text": "Explain how ...",
    "options": null,
    "correct_answer": "",
    "expected_answer": "Expected explanation details..."
  }}
]
"""

        try:
            response = get_gemini_response(prompt)

            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            elif clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()

            questions_data = json.loads(clean_response)
            if isinstance(questions_data, dict) and "questions" in questions_data:
                questions_data = questions_data["questions"]

            for i, q in enumerate(questions_data, start=1):
                Question.objects.create(
                    interview=interview,
                    question_text=q.get("question_text", f"Question {i}"),
                    question_type=q.get("question_type", "text"),
                    options=q.get("options"),
                    correct_answer=q.get("correct_answer", ""),
                    expected_answer=q.get("expected_answer", ""),
                    question_number=q.get("question_number", i)
                )

            questions = interview.questions.all().order_by("question_number")
            return render(request, 'interview/questions.html', {
                'interview': interview,
                'questions': questions
            })

        except Exception as e:
            # Delete empty interview session if question generation failed
            interview.delete()
            return render(request, 'interview/configuration.html', {
                'error': 'Our AI model is currently facing high demand. Please refresh and try again.'
            })

    return render(request, 'interview/configuration.html')


@login_required
def submit_interview(request, interview_id):

    interview = get_object_or_404(
        Interview,
        id=interview_id,
        user=request.user
    )

    if request.method == 'POST':

        questions = interview.questions.all()

        for question in questions:

            field_name = f'question_{question.id}'
            user_answer = request.POST.get(field_name, '').strip()

            # MCQ evaluation
            if question.question_type == 'mcq':

                if user_answer == question.correct_answer:
                    is_correct = True
                    score = 1
                else:
                    is_correct = False
                    score = 0

                Answer.objects.update_or_create(
                    question=question,
                    user=request.user,
                    defaults={
                        'answer': user_answer,
                        'is_correct': is_correct,
                        'score': score
                    }
                )

            # Text answer
            else:

                Answer.objects.update_or_create(
                    question=question,
                    user=request.user,
                    defaults={
                        'answer': user_answer,
                        'is_correct': None,
                        'score': None
                    }
                )

        interview.completed = True
        interview.save()

        return redirect(
            'interview_result',
            interview_id=interview.id
        )

    return redirect('interview')


@login_required
def interview_result(request, interview_id):

    interview = get_object_or_404(
        Interview,
        id=interview_id,
        user=request.user
    )

    answers = Answer.objects.filter(
        question__interview=interview,
        user=request.user
    )

    total_questions = answers.count()

    correct_answers = answers.filter(
        is_correct=True
    ).count()

    incorrect_answers = answers.filter(
        is_correct=False
    ).count()

    # MCQ score
    mcq_score = sum(
        answer.score or 0
        for answer in answers
    )

    mcq_questions = answers.filter(
        question__question_type='mcq'
    ).count()

    if mcq_questions:
        mcq_percentage = (
            mcq_score / mcq_questions
        ) * 100
    else:
        mcq_percentage = 0

    return render(
        request,
        'interview/result.html',
        {
            'interview': interview,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'incorrect_answers': incorrect_answers,
            'mcq_percentage': mcq_percentage,
        }
    )


@login_required
def interview_report(request, interview_id):

    interview = get_object_or_404(
        Interview,
        id=interview_id,
        user=request.user
    )

    answers = Answer.objects.filter(
        question__interview=interview,
        user=request.user
    ).select_related('question')

    for answer in answers:

        question = answer.question

        # Only evaluate text answers with AI
        if question.question_type == 'text':

            prompt = f"""
You are an expert technical interviewer.

Evaluate this candidate's answer.

Question:
{question.question_text}

Expected Answer:
{question.expected_answer}

Candidate Answer:
{answer.answer}

Give a score from 0 to 10.

Return ONLY valid JSON:
{{
    "score": 0,
    "correct": true,
    "feedback": "Detailed feedback",
    "missing_concepts": [],
    "technical_accuracy": "Good"
}}
"""

            try:
                response = get_gemini_response(prompt)

                clean_resp = response.strip()
                if clean_resp.startswith("```json"):
                    clean_resp = clean_resp[7:]
                elif clean_resp.startswith("```"):
                    clean_resp = clean_resp[3:]
                if clean_resp.endswith("```"):
                    clean_resp = clean_resp[:-3]
                clean_resp = clean_resp.strip()

                try:
                    evaluation = json.loads(clean_resp)
                    answer.score = evaluation.get('score')
                    answer.is_correct = evaluation.get('correct')
                    answer.feedback = evaluation.get('feedback')
                    answer.save()

                except json.JSONDecodeError:
                    answer.feedback = clean_resp
                    answer.save()

            except Exception:
                answer.feedback = "Our AI model is currently facing high demand. Please refresh to re-evaluate."
                answer.save()

    return render(
        request,
        'interview/report.html',
        {
            'interview': interview,
            'answers': answers
        }
    )


@login_required
def delete_interview(request, interview_id):

    interview = get_object_or_404(
        Interview,
        id=interview_id,
        user=request.user
    )

    if request.method == 'POST':
        interview.delete()

    return redirect('dashboard')


@login_required
def delete_all_interviews(request):

    if request.method == 'POST':
        Interview.objects.filter(user=request.user).delete()

    return redirect('dashboard')