from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import models
from django.db.models import CharField
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.sites.models import Site
from sorl.thumbnail import get_thumbnail
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from shortuuid.django_fields import ShortUUIDField
import logging

from django.contrib.postgres import search
from django.contrib.postgres import indexes

logger = logging.getLogger(__name__)


class User(AbstractUser):
    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = CharField(_("Name of User"), blank=True, max_length=255)

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})

    def has_profile(self) -> bool:
        """
        A convenience function to safely check if
        a user has a matching profile.
        """
        matching_profiles = Profile.objects.filter(user_id=self.id)
        if matching_profiles:
            return True

        return False


class Cluster(TagBase):
    class Meta:
        verbose_name = _("Cluster")
        verbose_name_plural = _("Clusters")


class TaggedCluster(TaggedItemBase):
    content_object = models.ForeignKey("Profile", on_delete=models.CASCADE)

    tag = models.ForeignKey(
        Cluster,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_items",
    )


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(_("phone"), max_length=254, blank=True, null=True)
    website = models.URLField(_("website"), max_length=200, blank=True, null=True)
    organisation = models.CharField(
        _("organisation"), max_length=254, blank=True, null=True
    )
    twitter = models.CharField(_("twitter"), max_length=254, blank=True, null=True)
    facebook = models.CharField(_("facebook"), max_length=254, blank=True, null=True)
    linkedin = models.CharField(_("linkedin"), max_length=254, blank=True, null=True)
    bio = models.TextField(_("bio"), blank=True, null=True)
    visible = models.BooleanField(_("visible"), default=False)
    location = models.CharField(_("location"), max_length=254, blank=True, null=True)
    photo = models.ImageField(
        _("photo"), blank=True, null=True, max_length=200, upload_to="photos"
    )

    tags = TaggableManager(blank=True)
    clusters = TaggableManager("Clusters", blank=True, through=TaggedCluster)

    # short_id is a unique identifier for a profile, used in the URL
    short_id = ShortUUIDField(length=8, unique=True, blank=True, null=True)

    # for tracking where this profile was imported from
    import_id = models.CharField(
        _("import_code"), max_length=254, blank=True, null=True
    )
    # we have these as cache tables because when we use object storage
    # we end up making loads of requests to AWS just to return an url
    _photo_url = models.URLField(blank=True, null=True)
    _photo_thumbnail_url = models.URLField(blank=True, null=True)
    _photo_detail_url = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")
        ordering = ["user__name"]

    @property
    def name(self):
        return self.user.name

    @name.setter
    def name(self, value):
        self.user.name = value

    @property
    def email(self):
        return self.user.email

    @property
    def admin(self):
        return self.user.is_staff

    @property
    def thumbnail_photo(self):
        if not self.photo:
            return None

        if self._photo_thumbnail_url:
            return self._photo_thumbnail_url

        return get_thumbnail(self.photo, "100x100", crop="center", quality=99).url

    @property
    def detail_photo(self):
        """
        A photo, designed for showing on a page, when viewing a profile,
        with a user's details

        """
        if not self.photo:
            return None

        if self._photo_detail_url:
            return self._photo_detail_url

        return get_thumbnail(self.photo, "250x250", crop="center", quality=99).url

    def __str__(self):
        if self.user.name:
            return f"{self.user.name} - {self.import_id}"
        else:
            return f"{self.user.first_name} - {self.import_id}"

    def get_absolute_url(self):
        return reverse("profile-detail", args=[self.short_id])

    def update_thumbnail_urls(self):
        """Generate the thumbnails for a profile"""
        if self.photo:
            self._photo_url = self.photo.url
            self._photo_thumbnail_url = get_thumbnail(
                self.photo, "100x100", crop="center", quality=99
            ).url
            self._photo_detail_url = get_thumbnail(
                self.photo, "250x250", crop="center", quality=99
            ).url

            self.save(
                update_fields=[
                    "_photo_thumbnail_url",
                    "_photo_detail_url",
                    "_photo_url",
                ]
            )

    def send_invite_mail(self):
        support_email_address = settings.SUPPORT_EMAIL
        rendered_templates = self.generate_invite_mail()

        send_mail(
            "Welcome to the Icebreaker One Constellation",
            rendered_templates["text"],
            support_email_address,
            [self.user.email],
            html_message=rendered_templates["html"],
        )

    def generate_invite_mail(self):
        support_email_address = settings.SUPPORT_EMAIL

        rendered_invite_txt = render_to_string(
            "invite_new_profile.txt",
            {"profile": self, "support_email_address": support_email_address},
        )
        rendered_invite_html = render_to_string(
            "invite_new_profile.mjml.html",
            {"profile": self, "support_email_address": support_email_address},
        )

        return {"text": rendered_invite_txt, "html": rendered_invite_html}


class Constellation(models.Model):
    """
    A Constellation is a name we give to a specific 'container' for the members
    using constellate. Constellations might have a description, some specific welcome text, and logo to members recognise it.
    """

    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profiles",
        verbose_name="site",
    )

    # logo = models.ImageField(_("photo"), blank=True, null=True, max_length=200)


class CATJoinRequest(models.Model):
    joined_at = models.DateTimeField()
    email = models.EmailField(unique=False)
    city_country = models.CharField(blank=True, max_length=256)
    # Why are you interested in joining?
    why_join = models.TextField(blank=True)
    # What's the main thing you'd like to offer as a part of the community?
    main_offer = models.TextField(blank=True)

    def __str__(self):
        return f"{self.joined_at.strftime('%Y-%m-%d')} - {self.email}"

    def bio_text_from_join_request(self):
        """
        Return a markdown version of the responses given when joining. Used to fill
        out a member's profile.
        """
        return f"""
### Why are you interested in joining?

{self.why_join}


### What's the main thing you'd like to offer as a part of the community?
{self.main_offer}
"""

    class Meta:
        indexes = [models.Index(fields=["email", "joined_at"])]
