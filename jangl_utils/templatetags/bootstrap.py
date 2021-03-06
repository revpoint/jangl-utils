from django import forms
from django.forms.forms import BoundField, BaseForm
from django.forms.utils import ErrorList
from django.template import Library, Context, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

register = Library()

TEMPLATE_ERRORS = 'bootstrap/_non_field_errors.html'
TEMPLATE_HORIZONTAL = 'bootstrap/_field_horizontal.html'
TEMPLATE_VERTICAL = 'bootstrap/_field_vertical.html'
TEMPLATE_DISPLAY = 'bootstrap/_field_display.html'


def render_non_field_errors(errors):
    if not errors:
        return ''
    context = {'errors': errors}
    return render_to_string(TEMPLATE_ERRORS, context)


def render_field(bound_field, show_label, template):
    widget = bound_field.field.widget

    if isinstance(widget, forms.RadioSelect):
        input_type = 'radio'
    elif isinstance(widget, forms.CheckboxSelectMultiple):
        input_type = 'multi_checkbox'
    elif isinstance(widget, forms.Select):
        input_type = 'select'
    elif isinstance(widget, forms.Textarea):
        input_type = 'textarea'
    elif isinstance(widget, forms.CheckboxInput):
        input_type = 'checkbox'
    elif isinstance(widget, (forms.FileInput)):
        input_type = 'file'
    elif issubclass(type(widget), forms.MultiWidget):
        input_type = 'multi_widget'
    else:
        input_type = 'input'

    context = {
        'bound_field': bound_field,
        'input_type': input_type,
        'show_label': show_label,
    }
    return render_to_string(template, context)


def as_bootstrap(obj, show_label, template):
    if isinstance(obj, BoundField):
        return render_field(obj, show_label, template)
    elif isinstance(obj, ErrorList):
        return render_non_field_errors(obj)
    elif isinstance(obj, BaseForm):
        non_field_errors = render_non_field_errors(obj.non_field_errors())
        fields = (render_field(field, show_label, template) for field in obj)
        form = ''.join(fields)
        return mark_safe(non_field_errors + form)
    else:
        raise TemplateSyntaxError('Filter accepts form, field and non fields '
                                  'errors.')


@register.filter
def as_horizontal_form(obj, show_label=True):
    return as_bootstrap(obj=obj, show_label=show_label,
                        template=TEMPLATE_HORIZONTAL)


@register.filter
def as_vertical_form(obj, show_label=True):
    return as_bootstrap(obj=obj, show_label=show_label,
                        template=TEMPLATE_VERTICAL)


@register.filter
def as_display_form(obj, show_label=True):
    form = as_bootstrap(obj=obj, show_label=show_label,
                        template=TEMPLATE_DISPLAY)
    return mark_safe(u'<div class="form-horizontal">{}</div>'.format(form))


@register.simple_tag
def render_widget(obj, **attrs):
    return mark_safe(obj.as_widget(attrs=attrs))


@register.filter
def glyphicon_bool(obj):
    glyph = '<span class="glyphicon {}"> </span>'.format(
        'glyphicon-ok-sign text-success' if obj else 'glyphicon-remove-sign text-danger'
    )
    return mark_safe(glyph)


@register.filter
def replace_underscore(val):
    return capfirst(val.replace('_', ' '))
