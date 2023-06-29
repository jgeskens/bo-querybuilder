from __future__ import unicode_literals
import importlib
import inspect
import json
from django.conf import settings
from django.contrib import messages
from django.db.models.base import ModelBase
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.translation import gettext
from advanced_reports.backoffice.base import BackOfficeView

from .models import SavedQuery
from .builder import QueryBuilder


class QueryBuilderView(BackOfficeView):
    template = 'backoffice/views/querybuilder.html'

    def __init__(self):
        qb_models = self.get_models_from_settings()
        self.qb = QueryBuilder(models=qb_models)

    def get_models_from_settings(self):
        model_paths = getattr(settings, 'QUERYBUILDER_MODELS', [])
        qb_models = []
        for model_path in model_paths:
            module_path, model_name = model_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            if model_name == '*':
                model_classes = inspect.getmembers(module, lambda c: type(c) == ModelBase)
                for model_tuple in model_classes:
                    qb_models.append(getattr(module, model_tuple[0]))
            else:
                model = getattr(module, model_name)
                qb_models.append(model)
        return qb_models

    def get_models(self, request):
        return self.qb.get_models()

    def execute_query(self, request):
        id = request.action_params.get('id')
        query = request.action_params.get('query')

        if id is not None:
            sq = SavedQuery.objects.get(pk=int(id))
            sq.last_run = now()
            sq.save()

        return self.qb.run(query)

    def save_query(self, request):
        query = request.action_params.get('query')
        name = request.action_params.get('name')
        existing_id = request.action_params.get('id')

        if existing_id is not None:
            sq = SavedQuery.objects.get(pk=existing_id)
            sq.name = name
            sq.query = json.dumps(query, indent=2)
            sq.save()
        else:
            sq = SavedQuery.objects.create(
                name=name,
                query=json.dumps(query, indent=2),
                created_by=request.user
            )
        messages.success(request, ugettext('Successfully saved query "%s"') % name)
        return sq.serialize()

    def get_saved_queries(self, request):
        queries = SavedQuery.objects.filter(created_by=request.user).order_by('-last_run')
        return {'queries': [query.serialize() for query in queries]}

    def delete_query(self, request):
        id = request.action_params.get('id')
        sq = SavedQuery.objects.get(pk=int(id))
        sq.delete()
        messages.success(request, ugettext('Successfully deleted query "%s"') % sq.name)

    def export_to_excel(self, request):
        id = int(request.GET.get('id'))
        sq = get_object_or_404(SavedQuery, pk=int(id))
        query = json.loads(sq.query)
        result = self.qb.run(query, stream=True)

        import xlsxwriter
        import StringIO
        output = StringIO.StringIO()
        wb = xlsxwriter.Workbook(filename=output, options=dict(in_memory=True))
        ws = wb.add_worksheet()
        for c, value in enumerate(query['values']):
            ws.write(0, c, value.get('label', value['expression']))
            ws.set_column(0, len(query['values'])-1, width=20)
        for r, obj in enumerate(result['objects']):
            for c, value in enumerate(query['values']):
                ws.write(r + 1, c, obj[value['expression']])
        wb.close()
        output.seek(0)

        filename = '%s.xlsx' % slugify(sq.name)
        response = HttpResponse()
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.write(output.read())

        return response
