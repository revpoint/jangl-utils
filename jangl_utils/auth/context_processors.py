

def user(request):
    return {
        'user': request.user,
        'account': request.account,
        'site': request.site,
    }
