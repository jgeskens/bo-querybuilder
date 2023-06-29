from __future__ import unicode_literals
import json
from django.contrib.auth.models import User

from django.db import models
from six import python_2_unicode_compatible, text_type
from django.utils.timezone import now
from django.utils.translation import gettext_lazy


@python_2_unicode_compatible
class SavedQuery(models.Model):
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))
    query = models.TextField(verbose_name=gettext_lazy('query'))
    created = models.DateTimeField(default=now, verbose_name=gettext_lazy('creation date'))
    created_by = models.ForeignKey(User, verbose_name=gettext_lazy('created by'), on_delete=models.CASCADE)
    last_run = models.DateTimeField(blank=True, null=True, verbose_name=gettext_lazy('last run'))

    class Meta:
        verbose_name = gettext_lazy('saved query')
        verbose_name_plural = gettext_lazy('saved queries')

    def __str__(self):
        return self.name

    def serialize(self):
        return {
            'id': self.pk,
            'name': self.name,
            'query': json.loads(self.query),
            'created': text_type(self.created),
            'created_by': self.created_by.get_full_name(),
            'last_run': self.last_run and text_type(self.last_run),
        }
