from jangl_utils import IS_PYPY

if IS_PYPY:
    from jangl_utils.kafka._pykafka.producers import *

else:
    from jangl_utils.kafka._confluent.producers import *
