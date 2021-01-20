from django.db.models import *
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AbstractUser, AbstractBaseUser
from django.contrib.postgres.fields import JSONField
from django.utils.crypto import get_random_string
import json
from django.db.models.signals import pre_save
import random
import string
from collections import defaultdict
import timeago
from multiselectfield import MultiSelectField
from fcm.models import AbstractDevice

ORDER_STATUSES = [('delivered', 'delivered'),
                ('on-the-way', 'on-the-way'),
                ('delayed', 'delayed'),
                ('pending', 'pending'),
                ('ready-to-pick-up', 'ready-to-pick-up'),
                ('confirmed', 'confirmed'),
                ('rejected', 'rejected'),
                ('rated', 'rated'),]

PAYMENT_METHODS = [('card', 'card'),
                ('cash', 'cash')]

NOTIFICATION_TARGET = (
                    ('1', 'User'),
                    ('2', 'Chef'),
                    )
WEEKDAYS = (
            ('1', 'Monday'),
            ('2', 'Tuesday'),
            ('3', 'Wednesday'),
            ('4', 'Thursday'),
            ('5', 'Friday'),
            ('6', 'Saturday'),
            ('7', 'Sunday'),
           )


class Dish(Model):
    name = CharField(max_length=60, blank=True)
    restaurant = ForeignKey('Restaurant', on_delete=CASCADE, related_name='dishes', null=True)
    description = CharField(max_length=300, blank=True)
    cookingTime = IntegerField(blank=True)  # in minutes
    price = DecimalField(max_digits=8, decimal_places=2)
    image = ImageField(upload_to ='backend/uploads/dishes/', blank=True) 
    isAvailable = BooleanField(default=True)
    foodType = ManyToManyField('FoodType', related_name="dishes", blank=True)
    created_at = DateTimeField(default=timezone.now)
    updated_at = DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    
    @property
    def rating(self):
        return self.restaurant.rating


class User(AbstractUser):
    username = CharField(max_length=60, blank=True)
    email = EmailField(unique=True)
    phone = CharField(max_length=60, blank=True)
    password = CharField(max_length=200, blank=True)
    isChef = BooleanField(default=False)
    favoriteDishes = ManyToManyField(Dish, blank=True)
    card = JSONField(blank=True, default=dict)
    addresses = JSONField(blank=True, null=True)
    created_at = DateTimeField(default=timezone.now)
    updated_at = DateTimeField(default=timezone.now)
    profileImage = ImageField(upload_to ="profile/", blank=True, null=True, default=None)
    latitude = DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, default=None)
    longitude = DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, default=None)
    stripeId = CharField(max_length=300, blank=True)
    isBanned = BooleanField(default=False)


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.username

    def create_superuser(self, username, email, password=None):
        user = self.create_user(username=username, email=email, password=password)
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def location(self):
        location = {"latitude": self.latitude,
                    "longitude": self.longitude,
                    "latitudeDelta": 0.1,
                    "longitudeDelta": 0.5}
        return location
    
    @property
    def preferedFoodTypes(self):
        type_counter = defaultdict(int)
        for order in self.orders.all():
            for product in order.products.all():
                for food_type in product.dish.foodType.all(): 
                    if food_type.name in type_counter:
                        type_counter[food_type.name] += 1
                    else:
                        type_counter[food_type.name] = 1
        return type_counter
  

class FoodType(Model):
    name = CharField(max_length=300, blank=True)
    image = ImageField(upload_to ='api/foodType/', blank=True, null=True, default=None)

    def __str__(self):
        return self.name

    @property
    def restaurants(self):
        dishes = self.dishes.all()
        r = []
        for dish in dishes:
            r.append(dish.restaurant)
        result = list(set(r))
        return result


class Restaurant(Model):
    name = CharField(max_length=60, blank=True)
    chef = ForeignKey('User', on_delete=CASCADE, related_name="chef", blank=True, null=True)
    description = CharField(max_length=300, blank=True)
    openingTime = CharField(max_length=10, blank=True)
    closingTime = CharField(max_length=10, blank=True)
    # isOpen = BooleanField(default=False)
    offersDelivery = BooleanField(default=False)
    coverDish = OneToOneField('Dish', 
                           on_delete=CASCADE, 
                           related_name='coverDish', 
                           blank=True, null=True)
    created_at = DateTimeField(default=timezone.now)
    updated_at = DateTimeField(default=timezone.now)
    address = CharField(max_length=200, blank=True)
    isAvailable = BooleanField(default=True)
    isAvailableToday = BooleanField(default=True)
    totalAcceptanceTime = FloatField(default=float(0))
    totalRejections = IntegerField(default=0)
    totalDelays = IntegerField(default=0)
    closedDays = MultiSelectField(choices=WEEKDAYS, default=[])
    lastPayment = DateTimeField(default=timezone.now)
    todayDish = OneToOneField('Dish', 
                           on_delete=SET_NULL, 
                           related_name='todayDish', 
                           blank=True, null=True)



    def __str__(self):
        return self.name

    @property
    def latitude(self):
        return self.chef.latitude

    @property
    def longitude(self):
        return self.chef.longitude

    @property
    def ordersNumber(self):
        return len(self.orders.all())

    @property
    def AVGprice(self):
        dishes = self.dishes.all()
        if dishes:
            return float(sum(dish.price for dish in dishes))/len(dishes)
        return None
    
    # @property
    # def foodType(self):
    #     ft = []
    #     dishes = self.dishes.all()
    #     for dish in dishes:
    #         ft += dish.foodType.all()
    #     print("foodtype", ft)
    #     return list(set(ft))

    @property
    def rating(self):
        reviews = self.reviews.all()
        if reviews:
            return float(sum(review.rate for review in reviews))/len(reviews)
        return 1

    @property
    def acceptance(self):
        ordersNumber = len(self.orders.all())
        if ordersNumber:
            return self.totalAcceptanceTime / ordersNumber
        else:
            return None

    @property    
    def rejectance(self):
        ordersNumber = len(self.orders.all())
        if ordersNumber:
            return self.totalRejections / ordersNumber
        else:
            return None
    
    @property    
    def delay(self):
        ordersNumber = len(self.orders.all())
        if ordersNumber:
            return self.totalDelays / ordersNumber
        else:
            return None


class OrderDish(Model):
    dish = ForeignKey('Dish', on_delete=CASCADE, related_name="orders")
    order = ForeignKey('Order', on_delete=CASCADE, related_name="products")
    amount = PositiveIntegerField()


class Order(Model):
    orderID = CharField(max_length=50, primary_key=True, editable=False)
    user = ForeignKey('User', on_delete=CASCADE, related_name="orders")
    restaurant = ForeignKey('Restaurant', related_name="orders", on_delete=CASCADE)
    status = CharField(max_length=25, choices=ORDER_STATUSES, default='pending')
    total = DecimalField(max_digits=8, decimal_places=2)
    deliverDate = JSONField(blank=False, default=dict)
    address = JSONField(blank=True)
    comment = CharField(max_length=300, blank=True)
    currency = CharField(max_length=10)
    isDelivery = BooleanField(default=False)
    created_at = DateTimeField(default=timezone.now)
    updated_at = DateTimeField(default=timezone.now)
    paymentMethod = CharField(max_length=4, choices=PAYMENT_METHODS, default='cash')
    chargeId = CharField(max_length=300, blank=True)
    completedOrderDate = DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.restaurant.name}: Delivery?{self.isDelivery} - {self.created_at} - {self.paymentMethod}\nOrder total: {self.total}"

    def restaurantName(self):
        return self.restaurant.name
    
    def restaurantId(self):
        return self.restaurant.pk

    @property
    def deliverDateTime(self):
        date = self.deliverDate["date"]
        time = self.deliverDate["time"].split("-")[0]
        datetime_str = "{} {}".format(date, time)
        try:
            dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            return dt
        except:    
            return None
    

class Review(Model):
    user = ForeignKey('User', on_delete=CASCADE)
    restaurant = ForeignKey('Restaurant', on_delete=CASCADE, related_name='reviews')
    order = ForeignKey('Order', on_delete=CASCADE, related_name='review')
    title = CharField(max_length=300, blank=True)
    description = CharField(max_length=1000, blank=True)
    rate = DecimalField(max_digits=2, decimal_places=1, default=5)
    timestamp = DateTimeField(default=timezone.now)


class Claim(Model):
    user = ForeignKey('User', on_delete=CASCADE, related_name='claims')
    order = ForeignKey('Order', on_delete=CASCADE, related_name='claims')
    claim = CharField(max_length=3000)
    image = ImageField(upload_to ='api/uploads/claims/', blank=True) 


class Notification(Model):
    user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='notifications')
    order = ForeignKey('Order', on_delete=CASCADE, related_name='notifications', null=True)
    actor = CharField(max_length=50)
    verb = CharField(max_length=50)
    action = CharField(max_length=50, blank=True)
    target = CharField(max_length=1, default='1', choices=NOTIFICATION_TARGET)
    description = TextField(blank=True)
    timestamp = DateTimeField(auto_now_add=True)
    isRead = BooleanField(default=False)
    isDeleted = BooleanField(default=False)
 
    def __str__(self):
        return f"{self.actor} {self.verb} {self.action} {self.target} at {self.timestamp}"

    @property
    def time_ago(self):
        now = timezone.now()
        time_ago = timeago.format(self.timestamp, now, "en_short").replace(" ago", "")
        return time_ago


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class MyDevice(AbstractDevice):
    user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='device')