from operator import attrgetter
from math import sqrt
import json
from django.db.models import Q
from django.shortcuts import render, redirect
from django.http.response import JsonResponse, HttpResponse
from django.conf import settings
from json import *
from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.parsers import JSONParser
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, renderer_classes, api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from .models import User, Dish, Restaurant, Review, Order, FoodType, OrderDish, Notification, Claim
from .serializers import UserSerializer, DishSerializer, OrderDishSerializer, \
                         RestaurantSerializer, ReviewSerializer, OrderSerializer, \
                         FoodTypeSerializer, ChangePasswordSerializer, NotificationSerializer
import stripe
from geopy.distance import distance as dist
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.utils.crypto import get_random_string
from django.core.mail import mail_admins
import string
from datetime import datetime, timezone, date, timedelta
from .permissions import RestaurantIsOwnerOrReadOnly, DishIsOwnerOrReadOnly, \
                         UserIsOwnerOrReadOnly, OrderIsOwnerOrReadOnly, \
                         OrderDishIsOwnerOrReadOnly, ReviewIsOwnerOrReadOnly, \
                         FoodTypeReadOnly, NotificationReadOnly
from fcm.utils import get_device_model, FCMMessage
from fcm.serializers import DeviceSerializer
from django.utils.translation import gettext as _


Device = get_device_model()

RIKO_CUSTOMER_FEE = 0.05
RIKO_CHEF_FEE = 0.1
RIKO_DELIVERY_FEE = 2000
CACHE_TTL = 60 * 15  # 15 minutes 

SERIALIZER_DICT = {'user': UserSerializer, 
                    'dish': DishSerializer, 
                    'restaurant': RestaurantSerializer, 
                    'review': ReviewSerializer, 
                    'order': OrderSerializer,
                    'foodType': FoodTypeSerializer,
                    'notification': NotificationSerializer,
                    'device': DeviceSerializer}

NOTIFICATION_TITLE = {"pending": "Tu orden ha sido creada",
                      "chef_pending": "Tienes una nueva orden",
                      "confirmed": "Tu orden ha sido confirmada",
                      "delayed": "Tu orden está atrasada",
                      "rejected": "Tu orden ha sido cancelada",
                      "ready-to-pick-up": "Tu orden está lista",
                      "on-the-way": "Tu orden va en camino",
                      "delivered": "Tu orden ha sido entregada"}

NOTIFICATION_TEXT = {
        "pending": "Te notificaremos cuando el chef acepte o rechace tu pedido",
        "chef_pending": "Ingresa a Mi Restaurant para aceptar o rechazar la orden",
        "confirmed": "Te notificaremos cuando tu orden esté lista para ser retirada en ",
        "confirmed_delivery": "Te notificaremos cuando tu orden esté lista para delivery",
        "delayed": "¡Lo sentimos mucho! El chef se ha retrasado con tu orden. Te notificaremos cuando tu orden esté lista para delivery o retiro",
        "rejected": "¡Lo sentimos! Actualmente el chef no tiene capacidad para servir tu orden",
        "ready-to-pick-up": "¡Buenas noticias! El pedido está listo para ser retirado en ",
        "on-the-way": "¡Atento! Tu pedido ya va en camino",
        "delivered": "Esperamos que disfrutes tu orden. Recuerda calificar tu pedido, tus comentarios son muy importantes para nosotros"}

def response(objects, model, request, many=True):
    serializer = SERIALIZER_DICT[model](objects, context={'request': request}, many=many)
    response = Response(serializer.data)
    response.accepted_renderer = JSONRenderer()
    response.accepted_media_type = "application/json"
    response.renderer_context = {}
    return response


def score(dish, user, user_location, params):
    prefered_foodtypes = user.preferedFoodTypes
    restaurant = dish.restaurant

    hist = sum(prefered_foodtypes[t.name] for t in dish.foodType.all())

    if restaurant.acceptance is not None:
        acceptance = restaurant.acceptance/params["avg_accept"]
    else:
        acceptance = params["min_accept"]/params["avg_accept"]

    if restaurant.rejectance is not None:
        rejectance = restaurant.rejectance/params["avg_reject"]
    else:
        rejectance = params["max_reject"]/params["avg_reject"]

    if restaurant.delay is not None:
        delays = restaurant.delay/params["avg_delay"]
    else:
        delays = params["max_delay"]/params["avg_delay"]

    if restaurant.ordersNumber:
        ordersNumber = restaurant.ordersNumber/params["avg_orders"]
    else:
        ordersNumber = params["min_orders"]/params["avg_orders"]
    
    if user_location:
        distance = dist((restaurant.latitude, restaurant.longitude), (user_location["latitude"], user_location["longitude"])).km
    else:
        distance = 0
        
    return hist + acceptance + ordersNumber - rejectance  - 0.5 * delays - distance


def notify(user_id, order_id, actor, verb, action='', target='', description='', isChef=False, isDelivery=False):
    user = User.objects.get(id=user_id)
    act = action if not isChef else "chef_" + action
    act = act if not isDelivery else act + "_delivery"
    notification = Notification.objects.create(user_id=user_id, 
                                               order_id=order_id,
                                               actor=actor, 
                                               verb=verb, 
                                               action=act, 
                                               target=target, 
                                               description=description)
    notification.save()
    for device in user.device.all():
        if device.is_active:
            device.send_message(title=NOTIFICATION_TITLE[act], 
                                body=NOTIFICATION_TEXT[act], 
                                data={"userId": user_id})
    return notification


@action(detail=False, methods=['post'])
@csrf_exempt
def recommendations(request):
    data = [json.loads(i) for i in request.POST.dict()][0]
    user_id, user_location, foodtype_name = data["userId"], data["location"], data["category"]
    user = User.objects.get(pk=user_id)
    restaurants = Restaurant.objects.all()
    params = {
        "avg_accept": sum(r.acceptance for r in restaurants if r.acceptance is not None)/len([r for r in restaurants if r.acceptance is not None]),
        "min_accept": min(r.acceptance for r in restaurants if r.acceptance is not None),
        "avg_reject": sum(r.rejectance for r in restaurants if r.rejectance is not None)/len([r for r in restaurants if r.rejectance is not None]),
        "max_reject": max(r.rejectance for r in restaurants if r.rejectance is not None),
        "avg_delay": sum(r.delay for r in restaurants if r.delay is not None)/len([r for r in restaurants if r.delay is not None]),
        "max_delay": max(r.delay for r in restaurants if r.delay is not None),
        "avg_orders": sum(r.ordersNumber for r in restaurants if r.ordersNumber != 0)/len([r for r in restaurants if r.ordersNumber != 0]),
        "min_orders": min(r.ordersNumber for r in restaurants if r.ordersNumber != 0),
             } 
    if foodtype_name == "Random":
        dishes = Dish.objects.filter(isAvailable=True, restaurant__isAvailable=True)
        dishes = sorted(dishes, key=lambda d: score(d, user, user_location, params), reverse=True)
    else:
        foodtype_dishes = []
        for d in Dish.objects.filter(isAvailable=True, restaurant__isAvailable=True):
            f_types = d.foodType.all()
            if foodtype_name in [f.name_en_us for f in f_types]:
                foodtype_dishes.append(d)
        dishes = sorted(foodtype_dishes, key=lambda d: score(d, user, user_location, params), reverse=True)
    return response(dishes, 'dish', request)


class CustomAuthToken(ObtainAuthToken):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        data = [json.loads(i) for i in request.POST.dict()][0]
        serializer = self.serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'phone': user.phone,
        })


class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    permission_classes = [permissions.IsAuthenticated,
                          DishIsOwnerOrReadOnly]

    @action(detail=True, methods=['patch'])
    @csrf_exempt
    def edit(request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        dish = Dish.objects.get(pk=pk)
        dish.name = data['name']
        dish.description = data['description']
        dish.price = data['price']
        dish.isAvailable = data['isAvailable']
        dish.cookingTime = data['cookingTime']
        dish.save()
        return response(dish, 'dish', request, False)
    

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated,
                          NotificationReadOnly]


class OrderDishViewSet(viewsets.ModelViewSet):
    queryset = OrderDish.objects.all()
    serializer_class = OrderDishSerializer
    permission_classes = [OrderDishIsOwnerOrReadOnly]


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [UserIsOwnerOrReadOnly]

    def create(self, request, format=None):
        user_info = request.data
        user = User.objects.create_user(username=user_info['username'],
                                        email=user_info['email'],
                                        phone=user_info['phone'] if 'phone' in user_info else '',
                                        isChef=True if 'isChef' in user_info else False,
                                        addresses={}, 
                                        card={})
        user.set_password(user_info['password'])
        user.is_active = True
        user.save()
        Device.objects.get(reg_id=user_info['fcmToken']).delete()  # DEVELOPMENT
        if user_info['fcmToken']:
            device = Device.objects.create(reg_id=user_info['fcmToken'],
                                           user_id=user.id,
                                           is_active=True)
            device.save()
        return response(user, 'user', request, False)

    @action(detail=True, methods=['post'])
    @csrf_exempt
    def update_device(request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        user = User.objects.get(pk=pk)
        device = Device.objects.filter(reg_id=data['fcmToken'])
        if device.exists():
            device[0].user = user
        else:
            device = Device.objects.create(reg_id=data['fcmToken'],
                                       user_id=user.id,
                                       is_active=True)
        device.save()
        return response(device, 'device', request, False)
        
        
    @action(detail=True, methods=['post'])
    @csrf_exempt
    def update_info(request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        user = User.objects.get(pk=pk)
        if "username" in data:
            user.username = data["username"]
        if "email" in data:
            user.email = data["email"]
        if "phone" in data:
            user.phone = data["phone"]
        if "profileImage" in data:
            user.profileImage = data["profileImage"]
        user.save()
        return response(user, 'user', request, False)
    
    
    @action(detail=True, methods=['post'])
    @csrf_exempt
    def update_password(request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        user = User.objects.get(pk=pk)
        old_password = data["oldPassword"]
        if not user.check_password(old_password):
            return Response({"oldPassword": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
        new_password = data["newPassword"]
        user.set_password(new_password)
        user.save()
        return response(user, 'user', request, False)


    @action(detail=True, methods=['post'])
    @csrf_exempt
    def update_credit_card(request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        user = User.objects.get(pk=pk)
        stripe.api_key = settings.STRIPE_APIKEY
        token = stripe.Token.create(
                    card={
                        "number": data["card"]["cardNumber"],
                        "exp_month": int(data["card"]["expiry"].split("/")[0][:-1]),
                        "exp_year": int(data["card"]["expiry"].split("/")[1][1:]),
                        "cvc": data["card"]["cvc"],
                    })
        card = token["card"]
        card["cardHolder"] = data["card"]["cardHolder"]
        card["token"] = token["id"]
        if card["exp_month"] > 9:
            card["expiry"] = str(card["exp_month"]) + " / " + str(card["exp_year"])[2:]
        else:
            card["expiry"] = "0" + str(card["exp_month"]) + " / " + str(card["exp_year"])[2:]
        user.card = card
        user.save()

        return response(user, 'user', request, False)

    @action(detail=True, methods=['post'])
    @csrf_exempt
    def update_address(request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        user = User.objects.get(pk=pk)
        user.addresses = data["addresses"]
        user.save()
        return response(user, 'user', request, False)

    @action(detail=True, methods=['post'])
    @csrf_exempt
    def add_favorite(request, user_pk, dish_pk):
        user = User.objects.get(pk=user_pk)
        dish = Dish.objects.get(pk=dish_pk)
        user.favoriteDishes.add(dish)
        user.save()
        return response(user, 'user', request, False)
    
    @action(detail=True, methods=['patch'])
    @csrf_exempt
    def remove_favorite(request, user_pk, dish_pk):
        user = User.objects.get(pk=user_pk)
        dish = Dish.objects.get(pk=dish_pk)
        user.favoriteDishes.remove(dish)
        user.save()
        return response(user, 'user', request, False)

    @action(detail=False)
    def favorites(request, user_pk):
        user = User.objects.get(pk=user_pk)
        favorites = user.favoriteDishes
        return response(favorites, 'dish', request)

    @action(detail=False)
    def inbox(request, user_pk):
        inbox = Notification.objects.filter(user_id=user_pk, isDeleted=False).order_by('-timestamp')
        return response(inbox, 'notification', request)

    @action(detail=False)
    def inbox_read(request, user_pk):
        inbox = Notification.objects.filter(user_id=user_pk, isDeleted=False).order_by('-timestamp')
        for notification in inbox:
            notification.isRead = True
            notification.save()
        return response(inbox, 'notification', request)

    @action(detail=False)
    def notifications_counter(request, user_pk):
        user = User.objects.get(pk=user_pk)
        inbox = Notification.objects.filter(user_id=user_pk, isDeleted=False, isRead=False)
        return JsonResponse({'counter': len(inbox)})

    @action(detail=False)
    def inbox_remove(request, user_pk, notification_pk):
        notification = Notification.objects.get(pk=notification_pk)
        notification.isDeleted = True
        notification.save()
        return response(notification, 'notification', request, False)
    
    @action(detail=False)
    @csrf_exempt
    def orders(request, user_pk):
        orders = Order.objects.filter(user_id=user_pk).order_by('-created_at')
        return response(orders, 'order', request)

    @action(detail=False, methods=['post'])
    @csrf_exempt
    def deactivate_notifications(request, user_pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        if data["fcmToken"] is not None:
            user = User.objects.get(id=user_pk)
            device = user.device.get(reg_id=data["fcmToken"])
            device.is_active = False
            device.save()
            return response(device, 'device', request, False)

    @action(detail=False, methods=['post'])
    @csrf_exempt
    def activate_notifications(request, user_pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        if data["fcmToken"] is not None:
            user = User.objects.get(id=user_pk)
            device = user.device.get(reg_id=data["fcmToken"])
            device.is_active = True
            device.save()
        return response(device, 'device', request, False)

    @action(detail=False, methods=['post'])
    @csrf_exempt
    def claim(request, user_pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        user = User.objects.get(id=user_pk)
        order = Order.objects.get(pk=data["orderId"])
        claim = data["claim"]
        if "image" in data:
            claim = Claim.objects.create(claim=claim,
                                         user_id=user_pk,
                                         order_id=data["orderId"],
                                         image=data["image"])
        else:
            claim = Claim.objects.create(claim=claim,
                                         user_id=user_pk,
                                         order_id=data["orderId"])
        claim.save()
        message = f"El usuario {user.username} ({user_pk}) ha realizado un reclamo por la orden {order.pk}\n\n"
        message += f"Reclamo: {claim}\n\n"
        message += f"Detalle de la orden:\n {str(order)}"
        mail_admins(subject=f"New claim on {order.restaurant.name}", message=message, html_message=None)
        return response(user, 'user', request, False)
    

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer 
    permission_classes = [RestaurantIsOwnerOrReadOnly]
    
    @csrf_exempt
    @action(detail=False)
    #@cache_page(CACHE_TTL)
    def popular(request):
        restaurants = Restaurant.objects.filter(isAvailable=True) #.order_by('-rating')[0:5]
        restaurants = sorted(restaurants, key=lambda t: t.rating)[0:5]
        # restaurants = Restaurant.objects.all()
        return response(restaurants, 'restaurant', request)

    @csrf_exempt
    @action(detail=False)
    #@cache_page(CACHE_TTL)
    def recently_added(request):
        restaurants = Restaurant.objects.filter(isAvailable=True).order_by('-created_at')[0:5]
        return response(restaurants, 'restaurant', request)

    #@cache_page(CACHE_TTL)
    @action(detail=False)
    def related(request, pk):
        restaurant = Restaurant.objects.get(pk=pk)
        restaurants = Restaurant.objects.filter(foodType=foodType)
        return response(restaurants, 'restaurant', request)

    #@action(detail=False)
    def reviews(request, pk):
        reviews = Review.objects.filter(restaurant_id=pk)
        return response(reviews, 'review', request)

    @action(detail=False)
    def dishes(request, pk):
        dishes = Dish.objects.filter(restaurant_id=pk)
        return response(dishes, 'dish', request)
    
    #@cache_page(CACHE_TTL)
    @action(detail=False)
    @csrf_exempt
    def near(request, pk):
        limit = 5
        user = User.objects.get(pk=pk)
        lat = user.location["latitude"]
        lng = user.location["longitude"]
        restaurants = sorted(Restaurant.objects.all(), 
                             key=lambda r: dist((r.chef.latitude, r.chef.longitude), (lat, lng)).km)[:limit]
        return response(restaurants, 'restaurant', request)
    
    #@cache_page(CACHE_TTL)
    @action(detail=False)
    @csrf_exempt
    def category(request, food_pk):
        restaurants = Restaurants.objects.filter(foodType_id=food_pk)
        return response(restaurants, 'restaurant', request)

    @action(detail=False, methods=['post'])
    @csrf_exempt
    def search(request):
        data = [json.loads(i) for i in request.POST.dict()][0]
        search = data["search"]
        restaurants = Restaurant.objects.filter(isAvailable=True)
        restaurants = restaurants.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return response(restaurants, 'restaurant', request)

    @action(detail=True)
    @csrf_exempt
    def availability(request, pk):
        restaurant = Restaurant.objects.get(pk=pk)
        return JsonResponse({"available": restaurant.isAvailable, 
                             "todayAvailable": restaurant.isAvailableToday})

    @action(detail=True, methods=['patch'])
    @csrf_exempt
    def change_availability(request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        restaurant = Restaurant.objects.get(pk=pk)
        restaurant.isAvailable = data["isAvailable"]
        restaurant.save()
        return response(restaurant, 'restaurant', request, False)

    @action(detail=True, methods=['patch'])
    @csrf_exempt
    def change_today_availability(request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        restaurant = Restaurant.objects.get(pk=pk)
        restaurant.isAvailableToday = data["isTodayAvailable"]
        restaurant.save()
        return response(restaurant, 'restaurant', request, False)

    @action(detail=False)
    @csrf_exempt
    def orders(request, pk):
        orders = Order.objects.filter(restaurant_id=pk)
        sorted(orders, key=lambda o: o.deliverDateTime)
        return response(orders, 'order', request)

    @action(detail=False)
    @csrf_exempt
    def pending_orders(request, pk):
        orders = Order.objects.filter(restaurant_id=pk, status='pending')
        # sorted(orders, key=lambda o: o.deliverDateTime)
        return response(orders, 'order', request)
    
    @action(detail=False)
    @csrf_exempt
    def confirmed_orders(request, pk):
        delayed_orders = list(Order.objects.filter(restaurant_id=pk, status='delayed'))
        confirmed_orders = list(Order.objects.filter(restaurant_id=pk, status='confirmed'))
        sorted(delayed_orders, key=lambda o: o.deliverDateTime)
        sorted(confirmed_orders, key=lambda o: o.deliverDateTime)
        return response(delayed_orders + confirmed_orders, 'order', request)

    @action(detail=False)
    @csrf_exempt
    def ready_orders(request, pk):
        orders = Order.objects.filter(restaurant_id=pk, status__in=('ready-to-pick-up', 'on-the-way'))
        # sorted(orders, key=lambda o: o.deliverDateTime)
        return response(orders, 'order', request)
    
    @action(detail=False)
    @csrf_exempt
    def orders_history(request, pk):
        orders = list(Order.objects.filter(restaurant_id=pk, status__in=('delivered', 'rejected', 'rated')).order_by('-created_at'))
        return response(orders, 'order', request)
    
    @action(detail=False)
    @csrf_exempt
    def earnings(request, pk):
        orders = Order.objects.filter(restaurant_id=pk, status__in=('delivered', 'rated'))
        today = datetime.now(timezone.utc)
        idx = (today.weekday() + 1) % 7
        sunday = today - timedelta(7+idx)
        sunday = sunday.replace(hour=11, minute=59)
        total_earnings = 0
        earnings = 0
        for order in orders:
            if order.completedOrderDate is not None:
                if order.completedOrderDate > sunday:
                    earnings += float(order.total) * (1 - RIKO_CHEF_FEE)
            total_earnings += float(order.total) * (1 - RIKO_CHEF_FEE)
        return JsonResponse({'earnings': earnings, 'total_earnings': total_earnings})

    @action(detail=False)
    @csrf_exempt
    def notifications_counter(request, pk):
        pending_orders = Order.objects.filter(restaurant_id=pk, status='pending')
        in_progress_orders = list(Order.objects.filter(restaurant_id=pk, status__in=('confirmed', 'delayed')))
        ready_orders = Order.objects.filter(restaurant_id=pk, status__in=('ready-to-pick-up', 'on-the-way'))
        return JsonResponse({'pendingCounter': len(pending_orders),
                             'inProgressCounter': len(in_progress_orders),
                             'readyCounter': len(ready_orders)})
    
    @action(detail=True, methods=['post', 'get'])
    @csrf_exempt
    def today_dish(request, pk):
        restaurant = Restaurant.objects.get(pk=pk)
        if request.POST:
            data = [json.loads(i) for i in request.POST.dict()][0]
            if restaurant.todayDish is not None:
                dish = restaurant.todayDish
                dish.name = data['name']
                dish.description = data['description']
                dish.price = data['price']
                dish.isAvailable = data['isAvailable']
                dish.cookingTime = data['cookingTime']
                dish.restaurant = restaurant
                dish.save()
            else:
                dish = Dish.objects.create(name=data['name'], description=data['description'],
                                           price=data['price'], isAvailable=data['isAvailable'],
                                           image="default.jpeg", cookingTime=data['cookingTime'],
                                           restaurant_id=pk)
                restaurant.todayDish = dish
                restaurant.save()
                dish.save()
        else:
            dish = restaurant.todayDish
            if dish is None:
                return HttpResponse(status=204)
        return response(dish, 'dish', request, False)
    

    @action(detail=False)
    @csrf_exempt
    def next_order(request, pk):
        delayed_orders = list(Order.objects.filter(restaurant_id=pk, status='delayed'))
        confirmed_orders = list(Order.objects.filter(restaurant_id=pk, status='confirmed'))
        sorted(delayed_orders, key=lambda o: o.deliverDateTime)
        sorted(confirmed_orders, key=lambda o: o.deliverDateTime)
        result = delayed_orders + confirmed_orders
        if result:
            return response(result[0], 'order', request, False)
        else:
            return response([], 'order', request)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [OrderIsOwnerOrReadOnly]

    def create(self, request, format=None):
        data = [json.loads(i) for i in request.POST.dict()][0]
        order = Order.objects.create(orderID=get_random_string(8, allowed_chars=string.ascii_uppercase + string.digits),
                                     user_id=data["userId"],
                                     isDelivery=data["isDelivery"],
                                    restaurant_id=data["restaurantId"],
                                    total=data["total"],
                                    deliverDate=data["date"],
                                    currency=data["currency"],
                                    address=data["address"],
                                    paymentMethod=data["paymentMethod"],
                                    comment=data["comment"])
        order.save()
        for product in data["products"]:
            order_dish = OrderDish.objects.create(order=order,
                                                  dish_id=product["dish_id"],
                                                  amount=product["quantity"])
            order_dish.save()
        # notify(data["userId"], order.orderID, "Your order", "has been created", order.status)
        chef_id = order.restaurant.chef.id
        notify(chef_id, order.orderID, "You", "have a new order", order.status, isChef=True, description=order.pk)
        return response(order, 'order', request, False)

    @action(detail=True, methods=['patch'])
    def accept(self, request, pk):
        order = Order.objects.get(pk=pk)
        user = User.objects.get(pk=order.user.id)
        stripe.api_key = settings.STRIPE_APIKEY
        amount = int(int(order.total)*(1 + RIKO_CUSTOMER_FEE))
        if order.isDelivery:
            amount += RIKO_DELIVERY_FEE
        if order.paymentMethod == 'card':
            if user.stripeId == "":
                customer = stripe.Customer.create(
                    source=user.card["token"],
                    email=user.email)
                charge = stripe.Charge.create(
                    amount=amount,
                    currency='CLP',
                    customer=customer.id)
                user.stripeId = customer.id
                user.save()
            else:
                charge = stripe.Charge.create(
                    amount=amount,
                    currency='CLP',
                    customer=user.stripeId)
            order.chargeId = charge["id"]
        order.status = 'confirmed'
        order.save()
        address = order.restaurant.address
        restaurant = order.restaurant
        restaurant.totalAcceptanceTime += (datetime.now(timezone.utc) - order.created_at).total_seconds() / 60.0
        restaurant.save()
        notify(order.user.id, order.orderID, "Your order", "has been accepted by the chef", 
               order.status, description=address, isDelivery=order.isDelivery)
        return response(order, 'order', request, False)

    @action(detail=True, methods=['patch'])
    def reject(self, request, pk):
        data = [json.loads(i) for i in request.POST.dict()][0]
        isChef = data["isChef"]
        order = Order.objects.get(pk=pk)
        refund = order.status != "pending" and isChef and order.paymentMethod == "card"
        if refund:
            stripe.api_key = settings.STRIPE_APIKEY
            resp = stripe.Refund.create(charge=order.chargeId)
        order.status = 'rejected'
        order.save()
        action = order.status if not refund else order.status + "_refund"
        if isChef:
            restaurant = order.restaurant
            restaurant.totalRejections += 1
            restaurant.save()
            notify(order.user.id, order.orderID, "Your order", "has been rejected by the chef", action)
        else:
            chef_id = order.restaurant.chef.id
            notify(chef_id, order.orderID, "Your order", "has been rejected by the user", action, isChef=True, description=pk)
        return response(order, 'order', request, False)
    
    @action(detail=True, methods=['patch'])
    def ready(self, request, pk):
        order = Order.objects.get(pk=pk)
        order.status = 'ready-to-pick-up'
        order.save()
        address = order.restaurant.address
        notify(order.user.id, order.orderID, "Your order", "is ready to pick-up", order.status, description=address)
        return response(order, 'order', request, False)
    
    @action(detail=True, methods=['patch'])
    def on_the_way(self, request, pk):
        order = Order.objects.get(pk=pk)
        order.status = 'on-the-way'
        order.save()
        notify(order.user.id, order.orderID, "Your order", "is on the way", order.status)
        return response(order, 'order', request, False)
    
    @action(detail=True, methods=['patch'])
    def delivered(self, request, pk):
        order = Order.objects.get(pk=pk)
        order.status = 'delivered'
        order.completedOrderDate = datetime.now() 
        order.save()
        if order.isDelivery:
            notify(order.restaurant.chef.id, order.orderID, "Your order", "has been delivered", 
                   order.status, isChef=True, isDelivery=True, description=order.orderID)
        notify(order.user.id, order.orderID, "Your order", "has been delivered", order.status)
        return response(order, 'order', request, False)
    
    @action(detail=True, methods=['patch'])
    def delayed(self, request, pk):
        order = Order.objects.get(pk=pk)
        order.status = 'delayed'
        order.save()
        restaurant = order.restaurant
        restaurant.totalDelays += 1
        restaurant.save()
        notify(order.user.id, order.orderID, "Your order", "is delayed", order.status)
        return response(order, 'order', request, False)


class FoodTypeViewSet(viewsets.ModelViewSet):
    queryset = FoodType.objects.all()
    serializer_class = FoodTypeSerializer
    permission_classes = [FoodTypeReadOnly]

    @action(detail=False)
    @method_decorator(cache_page(CACHE_TTL))
    def active(self, request):
        activeFoodTypes = []
        for restaurant in Restaurant.objects.all():
            for dish in restaurant.dishes.all():
                activeFoodTypes += dish.foodType.all()
        return response(list(set(activeFoodTypes)), 'foodType', request)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [ReviewIsOwnerOrReadOnly]

    def create(self, request, format=None):
        data = [json.loads(i) for i in request.POST.dict()][0]
        review = Review.objects.create(user_id=data["userId"],
                                       order_id=data["orderId"],
                                       restaurant_id=data["restaurantId"],
                                       rate=data["rate"],
                                       title=data["title"],
                                       description=data["description"])
        review.save()
        order = Order.objects.get(pk=data["orderId"])
        order.status = "rated"
        order.save()
        return response(review, 'review', request, False)


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer