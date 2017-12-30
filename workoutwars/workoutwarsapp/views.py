# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# workoutwarsapp/views.py
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, render_to_response
from django.template import RequestContext
from django.views.generic import TemplateView
from django.views.generic.edit import UpdateView
import datetime

from workoutwarsapp.forms import SignUpForm, AddWorkoutForm
from workoutwarsapp.models import User, Profile, Class, Team, Exercise, Workout

# Page views
class HomePageView(TemplateView):
    def get(self, request, **kwargs):
        return render(request, 'index.html', context=None)

@login_required
def scoreboard(request):
    classes = Class.objects.all()
    class_scores = []
    class_chart_data = []
    teams = Team.objects.all()
    team_scores = []
    team_chart_data = []

    for c in classes:
        c_workouts = Workout.objects.filter(user__profile__class_name=c)
        c_score = sum([workout.score for workout in c_workouts])
        c_count = len(Profile.objects.filter(class_name=c))
        if c_count == 0:
            c_normalized = 0
        else:
            c_normalized = c_score / c_count
        class_scores.append([c.plural, round(c_score, 2), round(c_normalized, 2)])
        class_chart_data.append([str(c.plural), round(c_normalized, 2)])

    for t in teams:
        t_workouts = Workout.objects.filter(user__profile__team=t)
        t_score = sum([workout.score for workout in t_workouts])
        t_count = len(Profile.objects.filter(team=t))
        if t_count == 0:
            t_normalized = 0
        else:
            t_normalized = t_score / t_count
        team_scores.append([t.name, round(t_score, 2), round(t_normalized, 2)])
        team_chart_data.append([str(t.name), round(t_normalized, 2)])

    try:
        recent_workouts = Workout.objects.all().order_by('workout_date')
    except ObjectDoesNotExist:
        recent_workouts = []

    return render(request,
        'scoreboard.html',
        {
            'class_scores': class_scores,
            'class_chart_data': class_chart_data,
            'team_scores': team_scores,
            'team_chart_data': team_chart_data,
        }
    )

@login_required
def coach(request):
    profiles = Profile.objects.all();
    total_durations = []
    exercise = Exercise.objects.get(name='Throwing')

    for p in profiles:
        try:
            workouts = Workout.objects.filter(user=p.user, exercise=exercise);
            durations = [w.duration for w in workouts]
        except ObjectDoesNotExist:
            workouts = []
            durations = []
        total_duration = round(sum(durations), 2)
        total_durations.append(total_duration)

    zipped = zip(profiles, total_durations)
    rankings = sorted(zipped, key=lambda x: x[1], reverse=True)

    page = request.GET.get('page', 1)

    paginator = Paginator(rankings, 10)
    try:
        rankings = paginator.page(page)
    except PageNotAnInteger:
        rankings = paginator.page(1)
    except EmptyPage:
        rankings = paginator.page(paginator.num_pages)

    return render(request,
        'coach.html',
        {
            'rankings': rankings,
        }
    )

@login_required
def indiv(request, username):

    # Get user and respective workouts
    user = User.objects.get(username=username)
    workouts = Workout.objects.filter(user=user)
    try:
        workouts = Workout.objects.filter(user=user).order_by('-workout_date')
        scores = [w.score for w in workouts]
    except ObjectDoesNotExist:
        workouts = []
        scores = []

    # Get statistics information
    num_workouts = len(workouts)
    total_points = round(sum(scores), 2)

    # Get line chart data
    start_date = datetime.date(2017, 12, 18)
    today = datetime.date.today()
    diff = (today - start_date).days
    chart_data = [[start_date + datetime.timedelta(days=x), 0] for x in range(0, diff + 1)]
    for w in workouts:
        diff = (w.workout_date - start_date).days
        if diff > 0 and diff < len(chart_data):
            chart_data[diff][1] += w.score

    # Pagination
    page = request.GET.get('page', 1)

    paginator = Paginator(workouts, 8)
    try:
        workouts = paginator.page(page)
    except PageNotAnInteger:
        workouts = paginator.page(1)
    except EmptyPage:
        workouts = paginator.page(paginator.num_pages)

    return render(request,
        'indiv.html',
        {
            'user': user,
            'workouts': workouts,
            'num_workouts': num_workouts,
            'total_points': total_points,
            'chart_data': chart_data
        }, {}
    )

@login_required
def feed(request):
    workouts = Workout.objects.all().order_by('-workout_date')
    page = request.GET.get('page', 1)

    paginator = Paginator(workouts, 10)
    try:
        workouts = paginator.page(page)
    except PageNotAnInteger:
        workouts = paginator.page(1)
    except EmptyPage:
        workouts = paginator.page(paginator.num_pages)

    index = paginator.page_range.index(workouts.number)
    max_index = len(paginator.page_range)
    start_index = index - 5 if index >= 5 else 0
    end_index = index + 5 if index <= max_index - 5 else max_index
    page_range = paginator.page_range[start_index:end_index]

    return render(request,
        'feed.html',
        {
            'workouts': workouts,
            'page_range': page_range,
        }
    )

@login_required
def rankings(request):
    profiles = Profile.objects.all();
    total_scores = []

    for p in profiles:
        try:
            workouts = Workout.objects.filter(user=p.user);
            scores = [w.score for w in workouts]
        except ObjectDoesNotExist:
            workouts = []
            scores = []
        total_score = round(sum(scores), 2)
        total_scores.append(total_score)

    zipped = zip(profiles, total_scores)
    rankings = sorted(zipped, key=lambda x: x[1], reverse=True)

    page = request.GET.get('page', 1)

    paginator = Paginator(rankings, 10)
    try:
        rankings = paginator.page(page)
    except PageNotAnInteger:
        rankings = paginator.page(1)
    except EmptyPage:
        rankings = paginator.page(paginator.num_pages)


    return render(request,
        'rankings.html',
        {
            'rankings': rankings
        }
    )


# Form views
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db() # load the profile instance created by the signals
            user.profile.nick_name = form.cleaned_data.get('nick_name')
            user.profile.class_name = form.cleaned_data.get('class_name')
            user.profile.team = form.cleaned_data.get('team')
            if not user.profile.nick_name:
                user.profile.nick_name = user.first_name + " " + user.last_name
            user.save()
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            return redirect('scoreboard')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def addworkout(request):
    if request.method == 'POST':
        form = AddWorkoutForm(request.POST)
        if form.is_valid():
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()
            return redirect('scoreboard')
    else:
        form = AddWorkoutForm()
    return render(request, 'add.html', {'form': form})

# @login_required
# def editworkout(request, pk):
#     instance = Workout.objects.get(id=pk)
#     form = AddWorkoutForm(request.POST or None, instance=instance)
#     if request.method == 'POST':
#         if form.is_valid():
#             instance = form.save(commit=False)
#             instance.user = request.user
#             instance.save()
#             return redirect('scoreboard')
#     else:
#         form = AddWorkoutForm()
#     return render(request, 'editworkout.html', {'form': form, 'exercise': instance.exercise})

@login_required
class editworkout(UpdateView):
    form_class = AddWorkoutForm
    model = Workout
    template_name = 'editworkout.html'

    def get(self, request, **kwargs):
        self.object = Workout.objects.get(id=self.kwargs['pk'])
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)

    def get_object(self, queryset=None):
        obj = Workout.objects.get(id=self.kwargs['pk'])
        return obj
