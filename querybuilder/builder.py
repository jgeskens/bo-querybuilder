from __future__ import unicode_literals
from collections import OrderedDict
from itertools import chain
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models.aggregates import Sum, Count
from django.db.models.fields import Field, PositiveIntegerField
from django.db.models.fields.related import ForeignKey
from django.db.models.loading import get_model
from django.utils.translation import ugettext_lazy
import six


EQUALITIES = (
    ('', ugettext_lazy('is equal to')),
    ('__icontains', ugettext_lazy('contains')),
    ('__istartswith', ugettext_lazy('starts with')),
    ('__iendswith', ugettext_lazy('ends with')),
    ('__in', ugettext_lazy('in')),
    ('__isnull', ugettext_lazy('is empty')),
    ('__gt', ugettext_lazy('is greater than')),
    ('__lt', ugettext_lazy('is lesser than')),
    ('__gte', ugettext_lazy('is greater than or equals')),
    ('__lte', ugettext_lazy('is lesser than or equals')),
    ('__day', ugettext_lazy('day is equal to')),
    ('__month', ugettext_lazy('month is equal to')),
    ('__year', ugettext_lazy('year is equal to')),
)


STRINGS = {
    'excludeText': ugettext_lazy('exclude'),
    'whereText': ugettext_lazy('where'),
    'equalsText': ugettext_lazy('equals'),
    'getText': ugettext_lazy('Get'),
    'newFilterText': ugettext_lazy('+ filter'),
    'newExcludeText': ugettext_lazy('+ exclude'),
    'runText': ugettext_lazy('Run'),
    'columnText': ugettext_lazy('column'),
    'saveQueryAsText': ugettext_lazy('save this query as'),
    'newQueryText': ugettext_lazy('new query'),
    'editText': ugettext_lazy('Edit'),
    'saveText': ugettext_lazy('Save'),
    'deleteText': ugettext_lazy('Delete'),
    'sumText': ugettext_lazy('sum'),
    'countText': ugettext_lazy('count'),
    'titleText': ugettext_lazy('title'),
    'exportToExcelText': ugettext_lazy('export to Excel'),
}


class QueryBuilder(object):
    def __init__(self, models=()):
        self.models = models

    def get_model_meta(self, model):
        opts = model._meta
        return {
            'verbose_name': opts.verbose_name,
            'verbose_name_plural': opts.verbose_name_plural,
            'fields': OrderedDict((field, self.get_field_meta(model, field)) \
                                  for field in opts.get_all_field_names() \
                                  if not field.endswith('_id')),
            'name': '%s.%s' % (opts.app_label, opts.model_name)
        }

    def get_models(self):
        return {
            'models': OrderedDict((m['name'], m) for m in [self.get_model_meta(model) for model in self.models]),
            'equalities': EQUALITIES,
            'strings': STRINGS,
        }

    def get_field_meta(self, model, field_name):
        queryset_choices = None
        model_admin = admin.site._registry.get(model)
        field, field_model, direct, m2m = model._meta.get_field_by_name(field_name)
        model_name, label = self.get_field_model(field)
        if (model_admin is None or not field_name in model_admin.raw_id_fields) and field_model is not None:
            if field_model.objects.count() < 101:
                queryset_choices = [(o.pk, six.text_type(o)) for o in field_model.objects.all()]
        return {
            'name': field_name,
            'model_name': model_name,
            'label': getattr(field, 'verbose_name', label),
            'choices': getattr(field, 'choices', queryset_choices),
            'direct': direct,
            'm2m': m2m
        }

    def get_field_model(self, field):
        if isinstance(field, ForeignKey):
            opts = field.related.parent_model._meta
            label = opts.verbose_name
        else:
            opts = getattr(field, 'opts', None)
            if opts is not None:
                label = opts.verbose_name_plural
            else:
                return None, None
        return '%s.%s' % (opts.app_label, opts.model_name), label

    def text_to_value_based_on_field(self, text, field):
        if text is None:
            return None
        if isinstance(field, Field):
            return field.__class__().to_python(text)
        else:
            return text

    def text_to_value(self, text, query, lookups):
        model_key = lookups[-2]['model'] if len(lookups) > 1 else query['model']
        app_label, model_name = model_key.split('.')
        model = get_model(app_label, model_name)
        lookup = lookups[-1]

        if lookup['equality'] == '__isnull':
            return True
        elif text is not None and lookup['equality'] in ('__day', '__month', '__year'):
            return PositiveIntegerField().to_python(text)

        if text is None:
            return None

        if not 'field' in lookup:
            return None

        field = model._meta.get_field_by_name(lookup['field'])[0]
        if lookup['equality'] == '__in':
            items = text.split(',')
            return [self.text_to_value_based_on_field(item, field) for item in items]
        return self.text_to_value_based_on_field(text, field)

    def run(self, query, stream=False):
        app_label, model_name = query['model'].split('.')
        model = get_model(app_label, model_name)
        qs = model.objects.all()
        p = '%s.objects' % model.__name__
        has_errors = False

        filters = []
        excludes = []
        for rule in query['rules']:
            filter_kwarg = '__'.join(lookup['field'] for lookup in rule['lookups'] if 'field' in lookup)
            filter_kwarg = '%s%s' % (filter_kwarg, rule['lookups'][-1].get('equality', ''))
            filter_value = rule['lookups'][-1].get('value')
            try:
                filter_value = self.text_to_value(filter_value, query, rule['lookups'])
            except ValidationError, e:
                rule['errors'] = e.messages
                has_errors = True
                filter_value = None
            if filter_value is not None:
                if rule.get('exclude', False):
                    #qs = qs.exclude(**{filter_kwarg: filter_value})
                    #p = '%s.exclude(%s=%s)' % (p, filter_kwarg, repr(filter_value))
                    excludes.append((filter_kwarg, filter_value))
                else:
                    #qs = qs.filter(**{filter_kwarg: filter_value})
                    #p = '%s.filter(%s=%s)' % (p, filter_kwarg, repr(filter_value))
                    filters.append((filter_kwarg, filter_value))


        qs = qs.filter(**dict(filters))
        p = '%s.filter(%s)' % (p, ', '.join('%s=%r' % fltr for fltr in filters))
        qs = qs.exclude(**dict(excludes))
        p = '%s.exclude(%s)' % (p, ', '.join('%s=%r' % excl for excl in excludes))


        values = [value['expression'] \
                  for value in query['values'] \
                  if 'expression' in value \
                  and not value.get('sum', False) \
                  and not value.get('count', False)]

        all_values = ['%s%s' % ('-' if value.get('sum') or value.get('count') else '',
                                value['expression']) \
                      for value in query['values']]

        qs = qs.values(*values)
        p = '%s.values(%s)' % (p, ', '.join(repr(value) for value in values))

        qs = qs.order_by(*all_values)
        p = '%s.order_by(%s)' % (p, ', '.join(repr(value) for value in values))

        sums = dict([(value['expression'], Sum(value['expression'])) \
                     for value in query['values'] \
                     if 'expression' in value \
                     and value.get('sum', False)])

        counts = dict([(value['expression'], Count(value['expression'])) \
                     for value in query['values'] \
                     if 'expression' in value \
                     and value.get('count', False)])

        annotates = {}
        annotates.update(sums)
        annotates.update(counts)

        psums = ('%s=Sum(%r)' % (sum, sum) for sum, _ in sums.iteritems())
        pcounts = ('%s=Count(%r)' % (cnt, cnt) for cnt, _ in counts.iteritems())

        if sums or counts:
            qs = qs.annotate(**annotates)
            p = '%s.annotate(%s)' % (p, ', '.join(chain(psums, pcounts)))


        # if not query['rules']:
        #     p = '%s.all()' % p
        # else:
        #     qs = qs.distinct()
        #     p = '%s.distinct()' % p

        count = qs.count() if not has_errors and not stream else None

        # Pagination
        if not 'page' in query:
            query['page'] = 1
        page = int(query['page'])
        items_per_page = 20

        if not stream:
            qs = qs[(page - 1) * items_per_page: page * items_per_page]
            objects = [(o.__dict__ if not isinstance(o, dict) else o) for o in qs] if not has_errors else None
        else:
            objects = ((o.__dict__ if not isinstance(o, dict) else o) for o in qs) if not has_errors else None

        return {
            'has_errors': has_errors,
            'query': query,
            'django': p if not has_errors else None,
            'objects': objects,
            'count': count,
            'sql': six.text_type(qs.query)
        }
