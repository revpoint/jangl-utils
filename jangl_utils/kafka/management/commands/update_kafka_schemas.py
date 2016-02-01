from optparse import make_option
from django.core.management.base import LabelCommand, CommandError
from jangl_utils.kafka.registry import get_producer, NotRegisteredError


class Command(LabelCommand):
    args = '<producer name> (<producer name> ...) [-c|--create] [-d|--dry-run] [-q|--quiet]'
    help = 'update kafka schemas with schema registry'
    label = 'producer'

    option_list = LabelCommand.option_list + (
        make_option(
            '-c',
            '--create',
            action='store_true',
            dest='skip_check',
            default=False,
            help='Create new schema (skips compatibility checks)'),
        make_option(
            '-t',
            '--test-compatibility',
            action='store_true',
            dest='test_compatibility',
            default=False,
            help='Check compatibility with schema server (does not update schema)'),
        make_option(
            '-q',
            '--quiet',
            action='store_true',
            dest='quiet',
            default=False,
            help='Hide output'),
    )

    def handle_label(self, label, **options):
        try:
            producer = get_producer(label)
        except NotRegisteredError:
            self.stderr.write('Could not find producer "{}"'.format(label))
        else:
            if producer.has_key:
                self.handle_schema(producer.key_schema, **options)
            self.handle_schema(producer.value_schema, **options)

    def handle_schema(self, schema, **options):
        if options.get('test_compatibility'):
            self.stdout.write('{} is {}compatible with existing schema'.format(
                schema.subject,
                '' if schema.test_compatibility() else 'not '
            ))
            if schema.already_exists():
                self.stdout.write('{} already exists'.format(schema.subject))
            else:
                self.stdout.write('{} does not exist'.format(schema.subject))
        else:
            if not options.get('quiet'):
                self.stdout.write('Updating {}'.format(schema))

            if options.get('skip_check'):
                schema.register_schema()
            else:
                schema.update_schema()

            if not options.get('quiet'):
                self.stdout.write(
                    'Schema ID: {}\n'
                    'Schema Version: {}\n'
                    'Schema Avro: {}\n\n'.format(
                        schema.schema_id,
                        schema.schema_version,
                        schema.schema_avro,
                    )
                )
