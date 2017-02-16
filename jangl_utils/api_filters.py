import operator
import re
import six
from django.db import models
from rest_framework.compat import distinct
from rest_framework.filters import BaseFilterBackend
from rest_framework.settings import api_settings


NON_ALPHANUMERIC = re.compile(r'[^\w\d]')


class BackendAPISearchFilter(BaseFilterBackend):
    # The URL query parameter used for the search.
    search_param = api_settings.SEARCH_PARAM
    api_search_param = 'search'

    def get_lookup_ids_from_search_term(self, request, url, search_term):
        search_request = request.backend_api.get(url, query_string={self.api_search_param: search_term})
        if search_request.ok:
            return [result['id'] for result in search_request.json()]
        return []

    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.query_params.get(self.search_param, '')
        return params.replace(',', ' ').split()

    def construct_text_search(self, field_name):
        if field_name.startswith('^'):
            return "%s__istartswith" % field_name[1:]
        elif field_name.startswith('='):
            return "%s__iexact" % field_name[1:]
        elif field_name.startswith('@'):
            return "%s__search" % field_name[1:]
        if field_name.startswith('$'):
            return "%s__iregex" % field_name[1:]
        else:
            return "%s__icontains" % field_name

    def filter_queryset(self, request, queryset, view):
        search_terms = self.get_search_terms(request)
        search_text_fields = getattr(view, 'search_text_fields', [])
        search_int_fields = getattr(view, 'search_int_fields', [])
        search_field_lookup = getattr(view, 'search_field_lookup', None)
        search_api_url = getattr(view, 'search_api_url', None)

        if not search_terms:
            return queryset

        base = queryset

        # First check all integer fields and return if matches
        int_queries = []
        for int_field in search_int_fields:
            values = filter(lambda x: x.isnumeric(), search_terms)
            if values:
                int_queries += [
                    models.Q(**{'{}__in'.format(int_field): values})
                ]

        if int_queries:
            int_queryset = queryset.filter(reduce(operator.or_, int_queries))
            if int_queryset:
                return int_queryset

        # If integer fields return nothing, use text lookup
        text_lookups = [
            self.construct_text_search(six.text_type(search_field))
            for search_field in search_text_fields
        ]

        for search_term in search_terms:
            queries = []
            if search_text_fields:
                cleaned_search_term = NON_ALPHANUMERIC.sub('', search_term)
                queries += [
                    models.Q(**{text_lookup: cleaned_search_term})
                    for text_lookup in text_lookups
                ]

            if search_field_lookup and search_api_url:
                lookup_ids = self.get_lookup_ids_from_search_term(request, search_api_url, search_term)
                if lookup_ids:
                    queries += [
                        models.Q(**{'{}__in'.format(search_field_lookup): lookup_ids})
                    ]

            if queries:
                queryset = queryset.filter(reduce(operator.or_, queries))

        # Filtering against a many-to-many field requires us to
        # call queryset.distinct() in order to avoid duplicate items
        # in the resulting queryset.
        return distinct(queryset, base)
