import requests
import enum
import functools

class HTTPMethod(enum.Enum):
    get = 1
    post_json = 2
    post_form = 3

class Endpoint:
    """represents a concrete http endpoint, requestable via the
    Provider.request method"""
    def __init__(self,
                 url,
                 method=HTTPMethod.get,
                 allow_redirects=True,
                 headers={},
                 parameters={},
                 # default response_hook just passes response
                 response_hook=lambda resp: resp):

        self.url = url
        self.method = method
        self.allow_redirects = allow_redirects
        self.headers = headers
        self.parameters = parameters
        self.response_hook = response_hook

class EndpointSequence:
    """represents a sequence of endpoints that can be consecutively requested
    via the Provider.request_sequence method. the first endpoint provided
    (the 'head' of the sequence) must be an endpoint. after that, each endpoint
    provided in the 'tail' can either be a function taking the response of the
    previous endpoint and producing a new endpoint or a concrete endpoint"""
    def __init__(self,
                 head,
                 *tail):

        self.head = head
        self.tail = tail

class Provider:
    def __init__(self,
                 proxies=None,
                 verify_certificates=True):

        self.session = requests.Session()
        self.proxies = proxies
        self.verify_certificates = verify_certificates

    def request(self,
                endpoint):

        url = endpoint.url
        method = endpoint.method
        headers = endpoint.headers
        parameters = endpoint.parameters
        response_hook = endpoint.response_hook
        allow_redirects = endpoint.allow_redirects

        # call
        resp = {
            HTTPMethod.get: \
            functools.partial(self.session.get, params=parameters),
            HTTPMethod.post_json: \
            functools.partial(self.session.post, json=parameters),
            HTTPMethod.post_form: \
            functools.partial(self.session.post, data=parameters)
        }.get(method)(url=url,
                      allow_redirects=allow_redirects,
                      headers=headers,
                      proxies=self.proxies,
                      verify=self.verify_certificates)

        # do any response mapping
        return response_hook(resp)

    def request_sequence(self,
                         sequence):

        def link(resp, endpoint):
            # check if the endpoint is a function
            if hasattr(endpoint, '__call__'):
                endpoint = endpoint(resp)

            return self.request(endpoint)

        return functools.reduce(link, sequence.tail, self.request(sequence.head))
