from tourism.models import Category, Commune, MainRepresentation, OpeningHours, \
    OpeningPeriod, Place, PointOfInterest, SubCategory, Tour, Variable, ZoneOfInterest
#
import datetime
import json
import os
from os.path import dirname, join
from django.contrib.gis.geos import fromstr
from django.core.files import File
from urllib.request import urlretrieve
#
#
def parse_dt_date(dt_date):
    return datetime.date(*map(int, dt_date.split("T")[0].split("-")))

#
def parse_dt_time(dt_time):
    return datetime.time(*map(int, dt_time.split(":")))

#
weekdays_reverse = {'Lundi': 1, 'Mardi': 2, 'Mercredi': 3, 'Jeudi': 4, 'Vendredi': 5, 'Samedi': 6, 'Dimanche': 7}
root_dir = join('tourism/data/tourism', 'objects')
#
## Create or get categories
event, _ = Category.objects.get_or_create(tag="event", defaults={"name":"Évènements", "order":2})
tourism_info, _ = Category.objects.get_or_create(tag="tourism-info", defaults={"name":"Accueil touristique", "order":4})
natural_site, _ = Category.objects.get_or_create(tag="natural-site", defaults={"name":"Sites naturels remarquables", "order":6})
city, _ = Category.objects.get_or_create(tag="city", defaults={"name":"Villages", "order":8})
cultural_site, _ = Category.objects.get_or_create(tag="cultural-site", defaults={"name":"Sites architecturaux remarquables", "order":10})
accommodation, _ = Category.objects.get_or_create(tag="accommodation", defaults={"name":"Hébergements", "order":12})
food, _ = Category.objects.get_or_create(tag="food-establishment", defaults={"name":"Restauration", "order":14})
tour, _ = Category.objects.get_or_create(tag="tour", defaults={"name":"Parcours de randonnées", "order":16})
#
i = 0
for subdir, dirs, files in os.walk(root_dir):
    for file in files:
        i += 1
        if i <= 304:
            continue
        with open(join(subdir, file)) as f:
            obj = json.load(f)
        if 'PointOfInterest' in obj['@type']:
            attributes = {}
            # Required attributes
            try:
                dt_id = obj["@id"]
                name = obj['rdfs:label']['fr'][0]
                latitude = obj['isLocatedAt'][0]['schema:geo']['schema:latitude']
                longitude = obj['isLocatedAt'][0]['schema:geo']['schema:longitude']
                location = fromstr(f'Point({longitude} {latitude})', srid=4326)
            except (KeyError, TypeError, IndexError):
                continue
            #
            ## Create Place
            print(f"\n\n===== {i} =====")
            poi = PointOfInterest(name=name, location=location, dt_id=dt_id)
            try:
                description = '\n\n'.join(obj['hasDescription'][0]['shortDescription']['fr'])
                poi.description = description
            except (KeyError, TypeError, IndexError):
                pass
            #
            # Get Category
            try:
                categories = obj['@type']
                if "EntertainmentAndEvent" in categories:
                    poi.category = event
                elif "Accommodation" in categories:
                    poi.category = accommodation
                elif "FoodEstablishment" in categories:
                    poi.category = food
                elif "Tour" in categories:
                    poi.category = tour
                elif "CulturalSite" in categories:
                    poi.category = cultural_site
                elif "NaturalHeritage" in categories:
                    poi.category = natural_site
                elif "PlaceOfInterest" in categories:
                    poi.category = tourism_info
            except (KeyError, TypeError, IndexError):
                pass
            #
            #
            #
            #
            # Add Optional attributes
            try:
                attributes['city'] = obj['isLocatedAt'][0]["schema:address"][0]["schema:addressLocality"]
            except (KeyError, TypeError, IndexError):
                pass
            #
            attr_map = {
                "street_address": (lambda o: '\n'.join(o['isLocatedAt'][0]["schema:address"][0]["schema:streetAddress"])),
                "dt_categories": (lambda o: "\n".join(o['@type'])),
                "email": (lambda o: o['hasContact'][0]['schema:email'][0]),
                "phone": (lambda o: o['hasContact'][0]['schema:telephone'][0]),
                "website": (lambda o: o['hasContact'][0]['foaf:homepage'][0]),
            }
            #
            for attr, dt_attr in attr_map.items():
                try:
                    attributes[attr] = dt_attr(obj)
                    print(f"\t\tAdd attribute {attr}")
                except (KeyError, TypeError, IndexError):
                    pass
            #
            #
            for k, v in attributes.items():
                setattr(poi, k, v)
            #
            #
            # Commune ...
            try:
                loc = obj['isLocatedAt'][0]["schema:address"][0]
                insee = loc["hasAddressCity"][0]["insee"]
                c = Commune.objects.get(insee=insee)
                poi.commune = c
            except (KeyError, TypeError, IndexError):
                print(f"\t!!No commune for this poi.")
                print("\t", file)
                pass
            except (Commune.DoesNotExist):
                insee = loc["hasAddressCity"][0]["insee"]
                print(f"\t!!INSEE {insee} does not exist in the db")
                pass
            #
            #
            poi.save()
            print(f"\tPOI {poi.pk} successfully created with place {poi.place_ptr.pk}")
            #
            #
            ## Main Representation
            try:
                main_media = obj['hasMainRepresentation'][0]
                mr = MainRepresentation(poi=poi)
                if "ebucore:hasAnnotation" in main_media:
                    annotation = main_media["ebucore:hasAnnotation"][0]
                    if "ebucore:title" in annotation:
                        mr.title = annotation["ebucore:title"]["fr"][0]
                    if "credits" in annotation:
                        mr.credits = annotation["credits"][0]
                #
                img_url = main_media["ebucore:hasRelatedResource"][0]["ebucore:locator"][0]
                img_name = os.path.basename(img_url)
                temp_filename, _ = urlretrieve(img_url)
                content = File(open(temp_filename, 'rb'))
                #
                mr.picture.save(img_name, content, save=True)
                print(f"\tMainRepresentation successfully created")
                #
            except (KeyError, TypeError, IndexError):
                print(f"\t!!No MainRepresentation created.")
                pass
            #
            ## OpeningPeriod & OpeningHours
            try:
                opening_hours_spec = obj['isLocatedAt'][0]["schema:openingHoursSpecification"]
                #
                for opening_hours in opening_hours_spec:
                    ## First step: Create a new OpeningPeriod if necessary
                    schema = OpeningPeriod()
                    if "schema:validFrom" in opening_hours:
                        schema.valid_from = parse_dt_date(opening_hours["schema:validFrom"])
                    else:
                        schema.valid_from = OpeningPeriod._meta.get_field("valid_from").get_default()
                    if "schema:validThrough" in opening_hours:
                        schema.valid_through = parse_dt_date(opening_hours["schema:validThrough"])
                    else:
                        schema.valid_through = OpeningPeriod._meta.get_field("valid_through").get_default()
                    # Datatourism's structure for openinghours allows duplicates
                    # for OpeningPeriod
                    # Fetch the relevant OpeningPeriod if it already exists
                    existing_schema_query = OpeningPeriod.objects.filter(
                        valid_from=schema.valid_from,
                        valid_through=schema.valid_through,
                        place=poi.place_ptr)
                    if existing_schema_query.count() != 0: # already exists
                        schema = existing_schema_query[0]
                    else:  # first time it is seen: Save it!
                        # print(schema)
                        schema.place = poi.place_ptr
                        schema.save()
                    #
                    ## Second step: Add Opening Hours for Each day
                    if not "schema:dayOfWeek" in opening_hours:
                        print("="*5, poi.name)
                    else:
                        for day_of_week in opening_hours["schema:dayOfWeek"]:
                            day_hours = OpeningHours()
                            day_hours.schema = schema
                            day_hours.weekday = weekdays_reverse[day_of_week['rdfs:label']['fr'][0]]
                            if "schema:opens" in opening_hours:
                                day_hours.from_hour = parse_dt_time(opening_hours["schema:opens"])
                            if "schema:closes" in opening_hours:
                                day_hours.to_hour = parse_dt_time(opening_hours["schema:closes"])
                            day_hours.save()
                print(f"\tOpeningPeriod successfully created")
            except (KeyError, TypeError, IndexError):
                print(f"\t!!No OpeninPeriod created.")
                pass