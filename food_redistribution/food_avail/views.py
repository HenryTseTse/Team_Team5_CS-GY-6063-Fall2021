from django.shortcuts import render, get_object_or_404
from .models import *
from .forms import FoodAvailForm, TimeSlotForm, BookingForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from accounts.models import Restaurant, FoodRedistributor
# from django.views.generic import CreateView, UpdateView

# from django.views.generic.base import View
from django.contrib import messages

# Create your views here.


def check_existing_post(request):
    data = request.POST.copy()
    data["author"] = request.user
    if len(FoodAvail.objects.filter(author=request.user)) > 0:
        return True
    else:
        return False


@login_required
def post_available_food(request):
    if not check_existing_post(request):
        instance = FoodAvail()
        data = request.POST.copy()
        data["author"] = request.user
        form = FoodAvailForm(data or None, instance=instance)
        if request.POST and form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse("food_avail:view_food_avail_res"))
    else:
        instance = get_object_or_404(FoodAvail, author=request.user)
        form = FoodAvailForm(request.POST, request.FILES, instance=instance)
        if request.method == "POST":
            form = FoodAvailForm(request.POST or None, instance=instance)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(reverse("food_avail:view_food_avail_res"))
        else:
            form = FoodAvailForm(instance=instance)
    return render(request, "food_avail/post_food_avail.html", {"food": form})


@login_required
def view_available_food(request):
    context = {}
    instance = FoodAvail.objects.get(author=request.user)
    meals_booked = 0
    bookings = Booking.objects.filter(restaurant=request.user)
    for b in bookings:
        meals_booked += b.meals_booked
    print(meals_booked)
    instance.food_available -= meals_booked
    if instance.food_available < 0:
        instance.food_available = 0
    context["food"] = instance
    print("FOOOOOD", context["food"])
    if request.method == "POST":
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        time_slot = TimeSlot()
        data = request.POST.copy()
        print("-----DATA----", data)
        data["time_slot_owner"] = request.user
        print("------DATA AFTER------", data)
        time_slot_owner = request.POST.get("time_slot_owner")
        print("PRINT CREATOR: ", time_slot_owner)
        print(
            TimeSlot.objects.filter(
                time_slot_owner=request.user, start_time=start_time, end_time=end_time
            )
        )
        if (
            len(
                TimeSlot.objects.filter(
                    time_slot_owner=request.user,
                    start_time=start_time,
                    end_time=end_time,
                )
            )
            == 0
        ):

            form = TimeSlotForm(data or None, instance=time_slot)
            if form.is_valid():
                # if time slot exists from 12-15, check if start time is between 12 and 15
                if TimeSlot.objects.filter(
                    start_time__lt=start_time, end_time__gt=start_time
                ).exists():
                    messages.info(request, "Time slots cannot overlap!")

                # if time slot exists from 12-15, check if end time is between 12 and 15
                elif TimeSlot.objects.filter(
                    start_time__lt=end_time, end_time__gt=end_time
                ).exists():
                    messages.info(request, "Time slots cannot overlap!")

                # if time slot exists from 12-15, check if start time and end time are between 12 and 15 (13, 14)
                elif TimeSlot.objects.filter(
                    start_time__lt=start_time, end_time__gt=end_time
                ):
                    messages.info(request, "Time slots cannot overlap!")

                # if time slot exists from 12-15, check if start time and time are both outside 12 and 15 (11-16)
                elif TimeSlot.objects.filter(
                    start_time__gt=start_time, end_time__lt=end_time
                ):
                    messages.info(request, "Time slots cannot overlap!")
                else:
                    form.save()
                    context["time_slot"] = form
            else:
                messages.info(request, "Start time cannot be after end time!")
        else:
            messages.info(request, "Time Slot Already Exists")

    time_slots_all = TimeSlot.objects.filter(time_slot_owner=request.user)
    context["time_slots_all"] = time_slots_all
    return render(request, "food_avail/view_food.html", context)


def update_time_slot(request, pk):
    instance = get_object_or_404(TimeSlot, pk=pk)
    form = TimeSlotForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse("food_avail:view_food_avail_res"))
    else:
        messages.info(request, "Start time cannot be after end time!")
    return render(request, "food_avail/update_time_slot.html", {"timeslot": form})


def delete_time_slot(request, pk):
    timeslot = get_object_or_404(TimeSlot, pk=pk)
    if request.method == "POST":
        timeslot.delete()
        # return HttpResponseRedirect(reverse("food_avail:view_food_avail_res"))
    return HttpResponseRedirect(reverse("food_avail:view_food_avail_res"))
    # return render(request, "food_avail/delete_time_slot.html", {"timeslot": timeslot})


def check_food_availibility(request):
    food = FoodAvail.objects.all()
    users_dict = {}
    users_lst = []
    for i in range(len(food)):
        user = {
            "author": None,
            "food_available": None,
            "description": None,
            "timeslot": None,
        }
        user["author"] = food[i].author.username
        meals_booked = 0
        bookings = Booking.objects.filter(restaurant=food[i].author)
        for b in bookings:
            meals_booked += b.meals_booked
        user["food_available"] = food[i].food_available - meals_booked
        if user["food_available"] < 0:
            user["food_available"] = 0
        user["description"] = food[i].description
        if TimeSlot.objects.filter(time_slot_owner=food[i].author):
            user["timeslot"] = TimeSlot.objects.filter(time_slot_owner=food[i].author)
        users_dict[food[i].author.username] = user
        users_lst.append(user)


    return render(request, "food_avail/view_food_avail.html", {"user_info": users_lst})


def bookings(request):
    timeslots = TimeSlot.objects.all()
    timeslots_avail = []
    for t in timeslots:
        if not Booking.objects.filter(bookings_owner=request.user, restaurant=t.time_slot_owner, start_time=t.start_time, end_time=t.end_time).exists():
            timeslots_avail.append(t) 
    # to_be_deleted = []
    # for t in timeslots_copy:
    #     if Booking.objects.filter(bookings_owner=request.user, restaurant=t.time_slot_owner, start_time=t.start_time, end_time=t.end_time).exists():
    #         to_be_deleted.append(t.id)
    # timeslots_copy.filter(id__in=to_be_deleted).delete()
    # print(timeslots)
    # print(timeslots_copy)
    return render(request, "food_avail/bookings.html", {'time_slot': timeslots_avail})

def create_booking(request):
    instance = Booking()
    data = request.POST.copy()
    print(data)
    bookings_owner_id = data["bookings_owner"]
    # print(bookings_owner_name)
    restaurant_id = data["restaurant"]
    # print(bookings_owner_name)
    print("DATAAAAAA", data)
    print("BOOKING OWNER", data["bookings_owner"])
    bookings_owner = User.objects.get(pk=bookings_owner_id)
    restaurant = User.objects.get(pk=restaurant_id)
    data["bookings_owner"] = bookings_owner
    data["restaurant"] = restaurant
    print(data)
    # data[]
    form = BookingForm(data or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        meals_booked = request.POST.get("meals_booked")
        meals_booked = int(meals_booked)
        print(type(meals_booked))
        
        curr_meals = FoodAvail.objects.get(author=restaurant).food_available
        prev_bookings_count = 0
        prev_bookings = Booking.objects.filter(restaurant=restaurant)
        for b in prev_bookings:
            prev_bookings_count += b.meals_booked
        print(type(curr_meals))
        if curr_meals - prev_bookings_count - meals_booked <= 0:
            messages.info(request, "No more meals available for pickup!")
        else:
            FoodAvail.objects.get(author=restaurant).food_available -= meals_booked
            print(FoodAvail.objects.get(author=restaurant).food_available)
            form.save()
            return HttpResponseRedirect(reverse("food_avail:view_bookings"))    
    return render(request, "food_avail/create_booking.html", {"booking": form})

def view_bookings(request):
    instance = Booking()
    data = request.POST.copy()
    print(data)
    booked = Booking.objects.filter(bookings_owner=request.user)    
    print(booked)

    return render(request, "food_avail/view_bookings.html", {"booked": booked})

def delete_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == "POST":
        booking.delete()
        # return HttpResponseRedirect(reverse("food_avail:view_food_avail_res"))
    return HttpResponseRedirect(reverse("food_avail:view_bookings"))

def calculate_meals_left(request):
    pass