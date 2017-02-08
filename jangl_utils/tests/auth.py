from jangl_utils.auth import User, CurrentAccount, Site


TEST_SUPERUSER_USER = User(
    user_id=1,
    email='superuser@test.com',
    first_name='Test',
    last_name='Superuser',
    buyers=[],
    vendors=[],
    affiliates=[],
    staff=[]
)

TEST_STAFF_USER = User(
    user_id=2,
    email='admin@test.com',
    first_name='Test',
    last_name='Admin',
    buyers=[],
    vendors=[],
    affiliates=[],
    staff=[{'is_admin': True}]
)
TEST_STAFF_ACCOUNT = CurrentAccount(TEST_STAFF_USER, 'staff')


TEST_BUYER_USER = User(
    user_id=3,
    email='buyer@test.com',
    first_name='Test',
    last_name='Buyer',
    buyers=[{'id': 1}],
    vendors=[],
    affiliates=[],
    staff=[]
)
TEST_BUYER_ACCOUNT = CurrentAccount(TEST_BUYER_USER, 'buyer-1')


TEST_VENDOR_USER = User(
    user_id=4,
    email='vendor@test.com',
    first_name='Test',
    last_name='Vendor',
    buyers=[],
    vendors=[{'id': 1}],
    affiliates=[],
    staff=[]
)
TEST_VENDOR_ACCOUNT = CurrentAccount(TEST_VENDOR_USER, 'vendor-1')


TEST_SITE = Site({'id': 1, 'name': 'Test Site'})
