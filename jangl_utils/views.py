from rest_framework import mixins, permissions, viewsets


class MultipleSerializerMixin(object):
    list_serializer_class = None
    detail_serializer_class = None
    create_serializer_class = None
    update_serializer_class = None

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()

        if self.action == 'list' and self.list_serializer_class:
            serializer_class = self.list_serializer_class
        elif self.action == 'retrieve' and self.detail_serializer_class:
            serializer_class = self.detail_serializer_class
        elif self.action == 'create' and self.create_serializer_class:
            serializer_class = self.create_serializer_class
        elif self.action == 'update' and self.update_serializer_class:
            serializer_class = self.update_serializer_class

        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)


class MultipleQuerysetMixin(object):
    list_queryset = None
    detail_queryset = None
    create_queryset = None
    update_queryset = None
    destroy_queryset = None

    read_queryset = None
    write_queryset = None

    def get_queryset(self):
        if self.action == 'list':
            list_queryset = self.get_list_queryset()
            if list_queryset:
                return list_queryset

        if self.action == 'retrieve':
            detail_queryset = self.get_detail_queryset()
            if detail_queryset:
                return detail_queryset

        if self.action == 'create':
            create_queryset = self.get_create_queryset()
            if create_queryset:
                return create_queryset

        if self.action == 'update':
            update_queryset = self.get_update_queryset()
            if update_queryset:
                return update_queryset

        if self.action == 'destroy':
            destroy_queryset = self.get_destroy_queryset()
            if destroy_queryset:
                return destroy_queryset

        if self.request.method in permissions.SAFE_METHODS:
            read_queryset = self.get_read_queryset()
            if read_queryset:
                return read_queryset

        if self.request.method not in permissions.SAFE_METHODS:
            write_queryset = self.get_write_queryset()
            if write_queryset:
                return write_queryset

        return super(MultipleQuerysetMixin, self).get_queryset()

    def get_list_queryset(self):
        return self.list_queryset

    def get_detail_queryset(self):
        return self.detail_queryset

    def get_create_queryset(self):
        return self.create_queryset

    def get_update_queryset(self):
        return self.update_queryset

    def get_destroy_queryset(self):
        return self.destroy_queryset


    def get_read_queryset(self):
        return self.read_queryset

    def get_write_queryset(self):
        return self.write_queryset


class MultiplePermissionsMixin(object):
    list_permission_classes = None
    detail_permission_classes = None
    create_permission_classes = None
    update_permission_classes = None
    destroy_permission_classes = None

    read_permission_classes = None
    write_permission_classes = None

    def get_permissions(self):
        permission_classes = self.permission_classes

        if self.action == 'list' and self.list_permission_classes:
            permission_classes = self.list_permission_classes
        elif self.action == 'retrieve' and self.detail_permission_classes:
            permission_classes = self.detail_permission_classes
        elif self.action == 'create' and self.create_permission_classes:
            permission_classes = self.create_permission_classes
        elif self.action == 'update' and self.update_permission_classes:
            permission_classes = self.update_permission_classes
        elif self.action == 'destroy' and self.destroy_permission_classes:
            permission_classes = self.destroy_permission_classes

        elif self.request.method in permissions.SAFE_METHODS and self.read_permission_classes:
            permission_classes = self.read_permission_classes
        elif self.request.method not in permissions.SAFE_METHODS and self.write_permission_classes:
            permission_classes = self.write_permission_classes

        return [permission() for permission in permission_classes]


class JanglViewSet(MultipleSerializerMixin, MultiplePermissionsMixin,
                   MultipleQuerysetMixin, mixins.ListModelMixin,
                   mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin, viewsets.GenericViewSet):
    pass


class JanglPlusDeleteViewSet(mixins.DestroyModelMixin, JanglViewSet):
    pass
