from django.urls import include, path
from django.conf.urls import url
from rest_framework import routers
from . import views
from django.contrib.auth import views as auth_views
from fcm.views import DeviceViewSet
from .models import User, Dish, Restaurant, Review, Order, OrderDish, Notification


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'dishes', views.DishViewSet)
router.register(r'restaurants', views.RestaurantViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'orders', views.OrderViewSet)
router.register(r'orderDishes', views.OrderDishViewSet)
router.register(r'foodType', views.FoodTypeViewSet)
router.register(r'notification', views.NotificationViewSet)
router.register(r'devices', DeviceViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path(r'recommendations/', views.recommendations, name="recommendations"),
    path(r'restaurants/popular', views.RestaurantViewSet.popular, name="popular"),
    path(r'restaurants/recently_added', views.RestaurantViewSet.recently_added, name="recently_added"),
    path(r'restaurants/near/<int:pk>/', views.RestaurantViewSet.near, name="near"),
    path(r'restaurants/<int:pk>/related', views.RestaurantViewSet.related, name="related"),
    path(r'restaurants/<int:pk>/reviews', views.RestaurantViewSet.reviews, name="reviews"),
    path(r'restaurants/<int:pk>/dishes', views.RestaurantViewSet.dishes, name="dishes"),
    path(r'restaurants/search', views.RestaurantViewSet.search, name="search"),
    path(r'restaurants/<int:pk>/availavility', views.RestaurantViewSet.availability, name="availability"),
    path(r'restaurants/<int:pk>/change_availavility', views.RestaurantViewSet.change_availability, name="change_availability"),
    path(r'restaurants/<int:pk>/change_today_availavility', views.RestaurantViewSet.change_today_availability, name="change_today_availability"),
    path(r'restaurants/<int:pk>/orders', views.RestaurantViewSet.orders, name="orders"),
    path(r'restaurants/<int:pk>/pending_orders', views.RestaurantViewSet.pending_orders, name="pending_orders"),
    path(r'restaurants/<int:pk>/confirmed_orders', views.RestaurantViewSet.confirmed_orders, name="in_progress_orders"),
    path(r'restaurants/<int:pk>/ready_orders', views.RestaurantViewSet.ready_orders, name="ready_orders"),
    path(r'restaurants/<int:pk>/orders_history', views.RestaurantViewSet.orders_history, name="orders_history"),
    path(r'restaurants/<int:pk>/earnings', views.RestaurantViewSet.earnings, name="earnings"),
    path(r'restaurants/<int:pk>/today_dish', views.RestaurantViewSet.today_dish, name="today_dish"),
    path(r'restaurants/<int:pk>/next_order', views.RestaurantViewSet.next_order, name="next_order"),
    path(r'restaurants/category/<int:food_pk>', views.RestaurantViewSet.search, name="category"),
    path(r'restaurants/<int:pk>/notifications_counter/', views.RestaurantViewSet.notifications_counter, name="restaurant_notifications_counter"),
    path(r'dishes/<int:pk>/edit', views.DishViewSet.edit, name="edit"),
    path(r'foodType/active', views.FoodTypeViewSet.active, name="active"),
    path(r'orders/<int:pk>/accept/', views.OrderViewSet.accept, name="accept"),
    path(r'orders/<int:pk>/reject/', views.OrderViewSet.reject, name="reject"),
    path(r'orders/<int:pk>/ready/', views.OrderViewSet.ready, name="ready"),
    path(r'orders/<int:pk>/on_the_way/', views.OrderViewSet.on_the_way, name="on_the_way"),
    path(r'orders/<int:pk>/delivered/', views.OrderViewSet.delivered, name="delivered"),
    path(r'orders/<int:pk>/delayed/', views.OrderViewSet.delayed, name="delayed"),
    path(r'users/<int:user_pk>/add_favorite/<int:dish_pk>', views.UserViewSet.add_favorite, name="add_favorite"),
    path(r'users/<int:user_pk>/remove_favorite/<int:dish_pk>', views.UserViewSet.remove_favorite, name="remove_favorite"),
    path(r'users/<int:user_pk>/favorites', views.UserViewSet.favorites, name="favorites"),
    path(r'users/<int:user_pk>/inbox_remove/<int:notification_pk>/', views.UserViewSet.inbox_remove, name="inbox_remove"),
    path(r'users/<int:user_pk>/inbox', views.UserViewSet.inbox, name="inbox"),
    path(r'users/<int:user_pk>/notifications_counter/', views.UserViewSet.notifications_counter, name="notifications_counter"),
    path(r'users/<int:user_pk>/activate_notifications/', views.UserViewSet.activate_notifications, name="activate_notifications"),
    path(r'users/<int:user_pk>/deactivate_notifications/', views.UserViewSet.deactivate_notifications, name="deactivate_notifications"),
    path(r'users/<int:user_pk>/inbox_read', views.UserViewSet.inbox_read, name="inbox_read"),
    path(r'users/<int:user_pk>/orders', views.UserViewSet.orders, name="orders"),
    path(r'users/<int:pk>/update_device', views.UserViewSet.update_device, name="update_device"),
    path(r'users/<int:pk>/update_info', views.UserViewSet.update_info, name="update_info"),
    path(r'users/<int:pk>/update_credit_card', views.UserViewSet.update_credit_card, name="update_credit_card"),
    path(r'users/<int:pk>/update_address', views.UserViewSet.update_address, name="update_address"),
    path(r'users/<int:pk>/update_password', views.UserViewSet.update_password, name="update_password"),
    path(r'users/<int:pk>/claim', views.UserViewSet.claim, name="claim"),
    url(r'^api-token-auth/', views.CustomAuthToken.as_view()),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^rest-auth/', include('rest_auth.urls')),
    url(r'^', include('django.contrib.auth.urls')),
    url(r'fcm/', include('fcm.urls')),
]