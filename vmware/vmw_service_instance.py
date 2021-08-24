from pyVim.connect import SmartConnect, Disconnect

def connect(args):
    try:
        if 'disable_ssl_verification' in args:
            service_instance = SmartConnect(host=args['host'],
                                            user=args['user'],
                                            pwd=args['password'],
                                            port=args['port'],
                                            disableSslCertValidation=True)
        else:
            service_instance = SmartConnect(host=args['host'],
                                            user=args['user'],
                                            pwd=args['password'],
                                            port=args['port'])
    except IOError as io_error:
        print(io_error)

    return service_instance
