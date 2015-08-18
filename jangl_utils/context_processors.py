

def account_names(request):
    def get_buyer_names(self):
        response = request.backend_api.get(('accounts', 'buyers', 'names'))
        if response.ok:
            return response.json()

    def get_vendor_names(self):
        response = request.backend_api.get(('accounts', 'vendors', 'names'))
        if response.ok:
            return response.json()

    return {
        'buyer_names': get_buyer_names(request),
        'vendor_names': get_vendor_names(request),
    }
