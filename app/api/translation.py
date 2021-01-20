from modeltranslation.translator import register, TranslationOptions
from .models import FoodType

@register(FoodType)
class FoodTypeTranslationOptions(TranslationOptions):
    fields = ('name',)