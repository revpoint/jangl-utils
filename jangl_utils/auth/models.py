from collections import namedtuple

USER_FIELDS = ('user_id', 'email', 'first_name', 'last_name',
               'buyers', 'vendors', 'staff')


class User(namedtuple('User', USER_FIELDS)):

    def __str__(self):
        return '#{0} - {1}'.format(self.id, self.name)

    def __repr__(self):
        return '<User {0}>'.format(str(self))

    @property
    def id(self):
        return self.user_id
    pk = id

    @property
    def username(self):
        return self.email

    @property
    def name(self):
        return '{0} {1}'.format(self.first_name, self.last_name) if self.first_name or self.last_name else self.email
    get_full_name = name

    def get_short_name(self):
        return '{0} {1}.'.format(self.first_name, self.last_name[0]) if self.last_name else self.first_name

    is_active = True
    is_superuser = False

    def set_password(self, raw_password):
        # set password
        pass

    def check_password(self, raw_password):
        from jangl_utils.auth import authenticate
        token = authenticate(email=self.email, password=raw_password)
        return token is not None

    def get_all_permissions(self, obj=None):
        return set()

    def has_perm(self, perm, obj=None):
        return True

    def has_perms(self, perm_list, obj=None):
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, module):
        return True

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def get_username(self):
        return self.email

    @property
    def is_staff(self):
        return bool(self.staff)

    @property
    def is_buyer(self):
        return bool(self.buyers)

    @property
    def is_vendor(self):
        return bool(self.buyers)

    def get_buyer(self, id):
        return _get_by_id(self.buyers, id)

    def get_vendor(self, id):
        return _get_by_id(self.vendors, id)

    def has_account(self, account):
        if account == 'staff':
            return self.is_staff
        try:
            _type, _id = account.split('-')
        except ValueError:
            pass
        else:
            if _type == 'buyer':
                return self.get_buyer(_id) is not None
            if _type == 'vendor':
                return self.get_buyer(_id) is not None
        return False


class AnonymousUser(object):
    id = None
    pk = None
    username = ''
    user_id = None
    is_staff = False
    is_active = False
    is_superuser = False
    first_name = None
    last_name = None
    email = None
    buyers = []
    vendors = []
    staff = None

    def __init__(self):
        pass

    def __str__(self):
        return 'AnonymousUser'

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return 1  # instances always return the same hash value

    def save(self):
        raise NotImplementedError("Cannot save anonymous user")

    def delete(self):
        raise NotImplementedError("Cannot delete anonymous user")

    def set_password(self, raw_password):
        raise NotImplementedError("Cannot set password for anonymous user")

    def check_password(self, raw_password):
        raise NotImplementedError("Cannot check password for anonymous user")

    def get_all_permissions(self, obj=None):
        return set()

    def has_perm(self, perm, obj=None):
        return False

    def has_perms(self, perm_list, obj=None):
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, module):
        return False

    def is_anonymous(self):
        return True

    def is_authenticated(self):
        return False

    def get_username(self):
        return self.username

    @property
    def is_staff(self):
        return False

    @property
    def is_buyer(self):
        return False

    @property
    def is_vendor(self):
        return False

    def get_buyer(self, id):
        pass

    def get_vendor(self, id):
        pass

    def has_account(self, account):
        return False


def _get_by_id(list, id):
        results = filter(lambda x: int(x['id']) == int(id), list)
        if len(results):
            return results[0]
