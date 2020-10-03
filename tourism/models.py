from django.conf import settings
from django.core.validators import MaxValueValidator
from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSGeometry

import datetime
from decimal import Decimal
# from django.utils.translation import gettext_lazy as _


class Variable(models.Model):
    name = models.CharField(max_length=20, unique=True, editable=False)
    value = models.FloatField()

    def __str__(self):
        return f"{self.name}={self.value}"


class Category(models.Model):
    name = models.CharField(max_length=150)
    tag = models.CharField(max_length=100, unique=True)
    order = models.IntegerField("ordre", default=100)

    light_color = models.CharField(max_length=7, default="#d54363")
    dark_color = models.CharField(max_length=7, default="#a1334b")

    class Meta:
        verbose_name = "categorie"
        verbose_name_plural = "categories"

    def __str__(self):
        return f"{self.name}"

def get_default_category():
    cat, created = Category.objects.get_or_create(tag="default", defaults={'order': 100})
    cat.icon = "grey"
    if not cat.name:
        cat.name = "(pas de catégorie)"
    cat.save()
    return cat.id


def icon_directory_path(instance, filename):
    return f"icon/{instance.category.tag}/{filename}"

class SubCategory(models.Model):
    name = models.CharField(max_length=150)
    icon = models.FileField(upload_to=icon_directory_path, verbose_name="icône")
    order = models.PositiveIntegerField("ordre")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        default=get_default_category
    )

    class Meta:
        verbose_name="sous-catégorie"
        verbose_name_plural="sous-catégories"

    def __str__(self):
        return f"{self.name}"


# == Commune ==
class Commune(models.Model):
    name = models.CharField("nom", max_length=50)
    geom = models.MultiPolygonField("géométrie", null=True)
    insee = models.CharField(max_length=5, unique=True)
    postal_code = models.CharField(max_length=5)
    in_argonne_pnr = models.BooleanField("fait partie du PNR ?")

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f"{self.name}"

# == POIs ==
class Place(models.Model):
    name = models.CharField("nom", max_length=100)
    description = models.TextField(blank=True)
    published = models.BooleanField("est publié", default=True)


    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        default=get_default_category
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    is_always_open = models.BooleanField("est en permanence ouvert", default=False, null=False, blank=False)

    def save(self, *args, **kwargs):
        ## Check that the selected subcategory belongs to the poi's category
        if self.subcategory and self.subcategory.category.pk != self.category.pk:
            self.subcategory = None
        super().save(*args, **kwargs)


class PointOfInterest(Place):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    note_of_interest = models.PositiveSmallIntegerField(
        default=0,
        validators=[
            MaxValueValidator(5),
        ]
    )

    location = models.PointField("localication")
    street_address = models.CharField("adresse", max_length=100, blank=True)
    commune = models.ForeignKey(
        Commune,
        on_delete=models.PROTECT,
    )
    
    dt_id = models.CharField(max_length=200)
    dt_categories = models.TextField(max_length=300)
    email = models.EmailField(max_length=50, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(max_length=200, blank=True)

    class Meta:
        ordering = ('name',)
        verbose_name = "point d'interêt"
        verbose_name_plural = "points d'interêt"

    def __str__(self):
        return f"{self.name} ({self.commune.name})"

class Tour(PointOfInterest):
    path = models.MultiLineStringField("parcours", null=True)
    distance = models.DecimalField("distance", max_digits=6, decimal_places=2, null=True) # km
    time = models.PositiveIntegerField("durée", null=True, blank=True) # min
    uphill = models.PositiveIntegerField("dénivelé positif", null=True, blank=True) # m
    downhill = models.PositiveIntegerField("dénivelé négatif", null=True, blank=True) # m
    elevation_min = models.PositiveIntegerField("altitude maximale", null=True, blank=True) # m
    elevation_max = models.PositiveIntegerField("altitude minimale", null=True, blank=True) # m
    is_closed = models.BooleanField("est une boucle", default=True)

    def compute_length(self):
        if self.path:
            length_m = self.path.transform(3035, clone=True).length  # change coordinates system
            length_km = round(length_m / 1000, 2)
            return Decimal(length_km)

    def get_is_closed(self, thresh=75):
        if self.path:
            if self.path.closed:
                return True
            else:
                p_start = GEOSGeometry("SRID=4326;POINT({} {})".format(*self.path[0][0]))
                p_end = GEOSGeometry("SRID=4326;POINT({} {})".format(*self.path[-1][-1]))
                p_start.transform(3035)
                p_end.transform(3035)
                return p_start.distance(p_end) <= thresh
        

    def save(self, *args, **kwargs):
        cat, created = Category.objects.get_or_create(tag="tour", defaults={'order': 100})
        self.category = cat
        if not self.distance and self.path:
            self.distance = self.compute_length()
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "randonnée"
        verbose_name_plural = "randonnées"

class Event():
    pass


class ZoneOfInterest(Place):
    zone = models.MultiPolygonField("zone")

    class Meta:
        ordering = ('name',)
        verbose_name = "zone d'interêt"
        verbose_name_plural = "zones d'interêt"


# == Management of opening hours ==
def get_valid_through_default():
        return datetime.date(datetime.date.today().year, 12, 31)

class OpeningPeriod(models.Model):
    """ Opening period """
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    valid_from = models.DateField("valable à partir du", default=datetime.date.today)
    valid_through= models.DateField("valable jusqu'au", blank=True, default=get_valid_through_default)


    class Meta:
        verbose_name = "période d'ouverture"
        verbose_name_plural = "périodes d'ouverture"
        ordering = ['valid_from', 'valid_through']

    def __str__(self):
        return f"{self.place.name} ({self.valid_from} - {self.valid_through}"



class OpeningHours(models.Model):
    """ Typical week's opening hours during a certain opening period (schema) """
    WEEKDAYS = [
        (1, "Lundi"),
        (2, "Mardi"),
        (3, "Mercredi"),
        (4, "Jeudi"),
        (5, "Vendredi"),
        (6, "Samedi"),
        (7, "Dimanche"),
    ]

    schema = models.ForeignKey(OpeningPeriod, on_delete=models.CASCADE)
    weekday = models.PositiveSmallIntegerField("jour de la semaine", choices=WEEKDAYS)
    from_hour = models.TimeField("heure d'ouverture", null=True)
    to_hour = models.TimeField("heure de fermeture", null=True)

    class Meta:
        verbose_name = "horaires d'ouverture"
        verbose_name_plural = "horaires d'ouverture"
        ordering = ['weekday', 'from_hour']

    def __str__(self):
        return f"{self.schema.place.name} {self.weekday} ({self.from_hour} - {self.to_hour})"

# == Media ==
class Media(models.Model):
    title = models.CharField("légende", max_length=150, null=True, blank=True)
    credits = models.CharField("crédits", max_length=100, null=True, blank=True)
    picture = models.ImageField()

    class Meta:
        abstract = True
        

def poi_directory_path(instance, filename):
    return f"poi_{instance.poi.id}/{filename}"

class MainRepresentation(Media):
    picture = models.ImageField(upload_to=poi_directory_path, verbose_name="image principale")
    poi = models.OneToOneField(
        PointOfInterest,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    class Meta:
        verbose_name = "image principale"
        verbose_name_plural = "images principales"