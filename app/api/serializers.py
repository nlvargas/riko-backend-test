from rest_framework import serializers
from rest_auth.serializers import PasswordResetSerializer
from django.contrib.auth.forms import PasswordResetForm
from .models import User, Dish, Restaurant, Review, Order, FoodType, OrderDish, Notification
from django.contrib.auth.password_validation import validate_password
from fcm.models import Device


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class PasswordSerializer(PasswordResetSerializer):
    def get_email_options(self):
        return {
            'subject_template_name': 'registration/password_reset_confirm.html',
            'email_template_name': 'registration/password_reset_confirm.html',
            'html_email_template_name': 'registration/'
                                    'password_reset_confirm.html',
            'extra_email_context': {
                'pass_reset_obj': {}
            }
        }


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'pk', 'username', 'email', 'password', 'phone',
                  'isChef', 'favoriteDishes', 'profileImage',
                  'addresses', 'card', 'chef', 'latitude', 'longitude')
        depth = 2


class DishSerializer(serializers.HyperlinkedModelSerializer):
    rating = serializers.ReadOnlyField()
    class Meta:
        model = Dish
        fields = ('id', 'pk', 'name', 'restaurant', 'description', 'foodType',
                  'cookingTime', 'price', 'image', 'isAvailable', 'rating', 'url')
        depth = 4


class RestaurantSerializer(serializers.HyperlinkedModelSerializer):
    foodType = serializers.ReadOnlyField()
    rating = serializers.ReadOnlyField()
    latitude = serializers.ReadOnlyField()
    longitude = serializers.ReadOnlyField()
    chef = UserSerializer(read_only=True, many=False)
    todayDish = DishSerializer(read_only=True, many=False)
    class Meta:
        model = Restaurant
        fields = ('pk', 'name', 'chef', 'foodType', 'description',
                  'rating', 'openingTime', 'closingTime',
                  'offersDelivery', 'dishes', 'coverDish', 'AVGprice', 'latitude', 'longitude',
                  'address', 'isAvailable', 'isAvailableToday', 'rating',
                  'closedDays', 'todayDish')
        depth = 3


class OrderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Order
        deliverDateTime = serializers.ReadOnlyField()
        fields = ('pk', 'user', 'restaurant', 'comment', 'status',
                  'address', 'total', 'deliverDate', 'orderID', 'products',
                  'restaurantName', 'restaurantId', 'currency', 'isDelivery',
                  'deliverDateTime')
        depth = 2


class OrderDishSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = OrderDish
        fields = ('order', 'dish', 'amount')
        depth = 1


class ReviewSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Review
        fields = ('user', 'restaurant', 'title', 'description', 'rate')
        depth = 1


class FoodTypeSerializer(serializers.HyperlinkedModelSerializer):
    restaurants = RestaurantSerializer(read_only=True, many=True)
    rating = serializers.ReadOnlyField()
    class Meta:
        model = FoodType
        fields = ('id', 'name', 'name_en_us', 'name_es', 'name_fr', 'image', 'restaurants', 'dishes', 'rating')
        depth = 4


class NotificationSerializer(serializers.HyperlinkedModelSerializer):
    time_ago = serializers.ReadOnlyField()
    class Meta:
        model = Notification
        fields = ('pk', 'user', 'verb', 'action', 'target', 'isRead', 'actor', 'description', 'timestamp', 'time_ago')
        depth = 1


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('dev_id', 'reg_id', 'name', 'is_active', 'user_id')
