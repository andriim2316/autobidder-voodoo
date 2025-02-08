from django.db import models

class Domain(models.Model):
    domain_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    expiration_date = models.DateTimeField()

    def __str__(self):
        return self.name


class AhrefsData(models.Model):
    domain = models.OneToOneField(
        Domain,
        on_delete=models.CASCADE,
        related_name="ahrefs_data",
        to_field="domain_id",
        primary_key=True
    )
    domain_rating = models.IntegerField(default=0)
    ahrefs_top = models.IntegerField(default=0)
    backlinks = models.IntegerField(default=0)
    ref_pages = models.IntegerField(default=0)
    pages = models.IntegerField(default=0)
    valid_pages = models.IntegerField(default=0)
    text_links = models.IntegerField(default=0)
    image_links = models.IntegerField(default=0)
    nofollow_links = models.IntegerField(default=0)
    ugc_links = models.IntegerField(default=0)
    sponsored_links = models.IntegerField(default=0)
    dofollow_links = models.IntegerField(default=0)
    redirect_links = models.IntegerField(default=0)
    canonical_links = models.IntegerField(default=0)
    gov_links = models.IntegerField(default=0)
    edu_links = models.IntegerField(default=0)
    rss_links = models.IntegerField(default=0)
    alternate_links = models.IntegerField(default=0)
    html_pages = models.IntegerField(default=0)
    internal_links = models.IntegerField(default=0)
    external_links = models.IntegerField(default=0)
    ref_domains = models.IntegerField(default=0)
    ref_class_c = models.IntegerField(default=0)
    ref_ips = models.IntegerField(default=0)
    linked_root_domains = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ahrefs Data for {self.domain.name}"


from django.db import models


class Bet(models.Model):
    domain = models.OneToOneField(
        Domain,
        on_delete=models.CASCADE,
        related_name="bet",
        db_column="domain_id",
        primary_key=True
    )
    expiration_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    max_bet = models.IntegerField()

    def __str__(self):
        return f"Bet for domain {self.domain_id} with max bet {self.max_bet}"