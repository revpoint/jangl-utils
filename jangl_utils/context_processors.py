
def account_names(request):
    return {
        'buyer_names': request.buyer_names,
        'vendor_names': request.vendor_names,
    }
