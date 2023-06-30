import json

from django.apps import apps
from django.conf import settings
from explorer.models import Query

from querybuilder.builder import QueryBuilder
from querybuilder.models import SavedQuery

SUPPORTED_APPS = list(set([
    entry.split('.')[0]
    for entry in settings.QUERYBUILDER_MODELS
]))


def get_models(app_labels):
    for app_label in app_labels:
        for model_class in apps.get_app_config(app_label).get_models():
            yield model_class


def convert_queries_to_sql_explorer():
    qb = QueryBuilder(list(get_models(SUPPORTED_APPS)))

    for sq in SavedQuery.objects.all():
        result = qb.run(json.loads(sq.query))

        sql = result['sql']
        suffix = 'LIMIT 20'
        if sql.endswith(suffix):
            sql = sql[:-len(suffix)]

        query = Query.objects.create(
            title=sq.name,
            sql=sql,
            created_by_user=sq.created_by
        )

        query.created_at = sq.created
        query.save()
