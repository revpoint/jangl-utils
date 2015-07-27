

def user(request):
    return {
        'user': getattr(request, 'user', None),
        'account': getattr(request, 'account', None),
        'site': getattr(request, 'site', None),
    }
