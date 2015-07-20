from rest_framework import serializers


class CurrentSiteMixin(serializers.Serializer):
    def validate(self, attrs):
        attrs = super(CurrentSiteMixin, self).validate(attrs)
        request = self.context.get('request')
        if request:
            attrs.setdefault('site', request.site)
        return attrs
