from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail

from interview_page.models import Interview, Question, Answer

import random
import os
from dotenv import load_dotenv

load_dotenv()


@login_required
def dashboard_view(request):
    interviews = Interview.objects.filter(user=request.user).order_by('-created_at')

    interview_cards = []
    total_mcq_scores = []
    unique_skills = set()

    for item in interviews:
        questions = item.questions.all()
        q_count = questions.count()
        answers = Answer.objects.filter(question__interview=item, user=request.user)

        mcq_answers = answers.filter(question__question_type='mcq')
        mcq_count = mcq_answers.count()
        mcq_correct = mcq_answers.filter(is_correct=True).count()

        score_pct = None
        if mcq_count > 0:
            score_pct = round((mcq_correct / mcq_count) * 100)
            total_mcq_scores.append(score_pct)

        # Extract skills for badges
        if item.skills:
            for s in item.skills.replace(',', ' ').split():
                clean_s = s.strip().title()
                if len(clean_s) > 1:
                    unique_skills.add(clean_s)

        interview_cards.append({
            'id': item.id,
            'skills': item.skills,
            'difficulty': item.difficulty,
            'interview_type': item.interview_type,
            'total_questions': q_count,
            'answers_count': answers.count(),
            'mcq_count': mcq_count,
            'mcq_correct': mcq_correct,
            'score_pct': score_pct,
            'completed': item.completed,
            'created_at': item.created_at,
        })

    total_interviews = interviews.count()
    completed_count = interviews.filter(completed=True).count()
    avg_score = round(sum(total_mcq_scores) / len(total_mcq_scores)) if total_mcq_scores else 0

    return render(request, 'dashboard.html', {
        'interview_cards': interview_cards,
        'total_interviews': total_interviews,
        'completed_count': completed_count,
        'avg_score': avg_score,
        'skills_list': sorted(list(unique_skills))[:10],
    })


def login_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        username_or_email = request.POST.get('username_or_email', '').strip()
        password = request.POST.get('password')

        # Check whether input is an email
        if '@' in username_or_email:

            try:
                user = User.objects.get(email=username_or_email)
                username = user.username

            except User.DoesNotExist:
                username = None

        else:
            username = username_or_email

        # Authenticate using username
        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect('dashboard')

        # Invalid credentials
        return render(request, 'login.html', {
            'error': 'Invalid username/email or password'
        })

    # GET request
    return render(request, 'login.html')


def register_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        # Check password:
        if password != confirm_password:
            return render(request, 'register.html', {
                'error': 'Passwords do not match!'
            })

        # Check username:
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {
                'error': 'Username already exists'
            })

        # Check email:
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {
                'error': 'Email already exists!'
            })

        # Generate OTP
        otp = random.randint(100000, 999999)

        # Store registration data temporarily in session:
        request.session['registration_data'] = {
            'username': username,
            'email': email,
            'password': password,
            'otp': otp
        }

        # Send OTP
        send_mail(
            subject='Your Registration OTP',
            message=f'Your OTP is {otp}. It is required to verify your email.',
            from_email=os.getenv("EMAIL_HOST_USER"),
            recipient_list=[email],
        )

        return redirect('verify_otp')

    return render(request, 'register.html')


def verify_otp_view(request):

    registration_data = request.session.get('registration_data')

    if not registration_data:
        return redirect('register')

    if request.method == 'POST':

        entered_otp = request.POST.get('otp')
        stored_otp = str(registration_data['otp'])

        if entered_otp == stored_otp:

            user = User.objects.create_user(
                username=registration_data['username'],
                email=registration_data['email'],
                password=registration_data['password']
            )

            # Remove registration data from session
            del request.session['registration_data']

            # Log the user in so they go straight to dashboard
            login(request, user)

            # Successfully verified
            return redirect('dashboard')

        else:

            # Wrong OTP
            return render(request, 'verify_otp.html', {
                'error': 'Invalid OTP'
            })

    # GET request
    return render(request, 'verify_otp.html')


def logout_view(request):

    logout(request)

    return redirect('login')