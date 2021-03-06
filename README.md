# django-clean-urls
Package for creation hierarchical clean URLs in Django.

## Overview
Django by default forces developers to use *static* URLs - by the word "static" I mean both fixed URL depth and that each URL is constant except some small chunks that change (usually instance's `pk` and/or `slug`). This works fine 'till you get some hierarchy of unpredictable depth in your models.

Consider an example:
```python
    class Category(MPTTModel):  # MPTTModel is a class from `django-mptt`, it allows to create tree structures with Categories as nodes
        parent = TreeForeignKey('self')  # foreign key to parent Category
        slug = ...
        ...

    class Photo(models.Model):
        category = models.ForeignKey('Category')
        slug = ...
        ...
```

Usually you create urlpattern like this:
```python
    r'^gallery/(?P<category_slug>[-\w]+)/(?P<photo_slug>[-\w]+)$'
```

Therefore you restrict all your URLs to be as:

    /gallery/mountains/mountain-photo/

It is quite human-readable (and fast!), but you lose all Category's hierarchy. You'd better have URLs like this:

    /gallery/nature/mountains/mountain-photo/
    /gallery/nature/animals/frogs/green-frogs/green-frog-in-water/
    /gallery/portraits/jina/

These URLs are ["clean" / "semantic"](https://en.wikipedia.org/wiki/Semantic_URL), and django-clean-urls will help you to create them easily.

## Third-party app support
Django-clean-urls supports two main tree-structure apps for Django:

- django-mptt
- django-treebeard

However, it's super easy to work with *any* hierarchy, no matter how you organize it.

## Requirements
- django (tested on but not restricted to v1.10)

## Example
TIP: All of the source code described below is available in *example* folder. It is a test project already set-up and ready-to-go, so you can clone and play with it (administrator login/password: admin/rootroot):

    mkdir /tmp/clean_urls && cd /tmp/clean_urls
    pyvenv env && source env/bin/activate
    pip install django django-mptt pillow django-clean-urls
    git clone https://github.com/c0ntribut0r/django-clean-urls
    cd django-clean-urls/example
    ./manage.py runserver    

Let's create a photos portfolio (gallery) app with super-complicated hierarchy where we'll cover all use-cases of django-clean-urls.

#### Depth 1: Photographer

First, lets create a Photographer model (pretty easy one).
```python
    # gallery/models.py
    from django.db import models

    class Photographer(models.Model):
        slug = models.SlugField()
        # ...
```

Now, lets create "clean url" pattern. Comments explain what's going on.
```python
    # gallery/urls.py
    from django.conf.urls import url

    from clean_urls.views import CleanURLHandler

    from .models import Photographer
    from .views import HomeView, PhotographerView


    app_name = 'gallery'
    urlpatterns = [
        url(
            r'^(?P<slug>([-\w]+/)+)$',  # very generic regex
            CleanURLHandler(  # this class will do all dirty work for us
                (Photographer.objects.all(), PhotographerView.as_view()),  # search through all photographers and call PhotographerView on success
            ),
            name='generic'  # needed for reverse url resolution; call it "generic" because this url can point to many different objects
        ),
    ]
```

We've successfully set up simple clean url - it will fire PhotographerView at these urls:

    /jane/
    /jill/

Once CleanURLHandler gets slug `jill`, it searches for an instance in `Photographer.objects.all()` with `slug` field containing 'jill', and passes it to PhotographerView as `instance` kwarg. Now let's create the PhotographerView:
```python
    # gallery/views.py
    from django.views.generic import DetailView

    class PhotographerView(DetailView):
        template_name = 'gallery/photographer.html'

        def dispatch(self, *args, **kwargs):  # already resolved instance here!
            self.instance = kwargs.pop('instance')  # save instance
            return super().dispatch(*args, **kwargs)

        def get_object(self, queryset=None):
            return self.instance  # use saved instance
```

One more thing to do still remains - reverse url resolution (again, see comments):
```python
    # gallery/models.py
    from django.core.urlresolvers import reverse
    ...

    class Photographer(models.Model):
        # ...
        def get_absolute_url(self):
            return reverse('gallery:generic', kwargs={'slug': self.get_slug()})  # CleanURLHandler automatically created 'get_slug' method; for this simple model it will just return self.slug
```

That's it - now calling `Photographer.objects.get(slug='jill').get_absolute_url()` will return `/jill/`.

Now we need to go deeper ©

#### Depth 2: Categories
Now let's make our app more complex. Let's allow each photographer to have his own categories tree structure. We'll use django-mptt for this purpose.
```python
    # gallery/models.py
    from mptt.models import MPTTModel, TreeForeignKey

    class Category(MPTTModel):
        photographer = models.ForeignKey('Photographer')
        parent = TreeForeignKey('self', blank=True, null=True)
        slug = models.CharField('slug', max_length=32)

        def get_absolute_url(self):
            return reverse('gallery:generic', kwargs={'slug': self.get_slug()})
```

Have a look at new `urls.py`:
```python
    urlpatterns = [
        # ...
        url(
            r'^(?P<slug>([-\w]+/)+)$',
            CleanURLHandler(
                (Photographer.objects.all(), PhotographerView.as_view()),
                (Category.objects.all(), CategoryView.as_view()),  # here we state that Photographer may contain a Category within
            ),
            name='generic'
        ),
    ]
```

Now `CleanURLHandler` knows that `Category` is `Photographer`'s child and can access its parent through `photographer` field.
> *How does CleanURLHandler know about ForeignKey from Category to Photographer?*
> Answer: It searches for ForeignKey or OneToOneKey from Category to Photographer. If there is exactly one such field, there will be created method called "get_parent" which follows the relation. Otherwise you need manually create "get_parent" method.

`CleanURLHandler` also sees that `Category` is of `MPTTModel` (it is a tree structure, in other words), and "expands" it so that slug may be like

   jane/root-category/subcategory/subsubcategory/

#### Depth 3: Photos
We still lack photos in our gallery app. Let's fix this!
```python
    # gallery/models.py

    class Photo(models.Model):
        categories = models.ManyToManyField('Category')
        image = models.ImageField('image')
        slug = models.SlugField()

        def get_absolute_url(self):
            return reverse('gallery:generic', kwargs={'slug': self.get_slug})

    # gallery/urls.py
        # ...
        url(
            r'^(?P<slug>([-\w]+/)+)$',
            CleanURLHandler(
                (Photographer.objects.all(), PhotographerView.as_view()),
                (Category.objects.all(), CategoryView.as_view()),
                (Photo.objects.all(), PhotoView.as_view()),  # and Category may contain Photos within
            ),
            name='generic'
        ),
```

Look carefully at `models.py`: any photo may reside in several categories (ManyToManyField). That's meaningful: if photo contains a person in the forest, it fits both "people" and "nature" categories. `CleanURLHandler` cannot guess how to get parent `Category` for any `Photo` instance, and raises an exception:

    django.core.exceptions.ImproperlyConfigured: Cannot reslove relation from <class 'gallery.models.Photo'> to <class 'gallery.models.Category'>

To fix this, let's define `get_parent` method:
```python
    # gallery/models.py
    class Photo(models.Model):
        categories = models.ManyToManyField('Category')
        ...

        def get_parent(self):
            return self.categories.first()  # by default, the first category will be treated as parent
```

So, if `Photo` "Maria" is in both "People" and "Nature" categories, its slug will be **only one** of
- jane/people/maria/maria-on-the-shore/
- jane/nature/maria-on-the-shore/
depending on what `self.categories.first()` returns.

#### Breadcrumbs
Every model defined in `CleanURLHandler` also has a method `get_parents` which will return all parents including the instance itself - nice feature for breadcrumbs generation! For example,
```python
    In [4]: Photo.objects.get(slug='maria-on-the-shore').get_parents()
    Out[4]: 
    [<Photographer: jane>,
     <Category: People>,
     <Category: Maria>,
     <Photo: maria-on-the-shore>]
```
