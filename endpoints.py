import functools
import moya
import model

class StreamerDoesNotExist(BaseException):
    pass

client_id_header = {
    'Client-ID': 'i3gy18ug10vof5paxn37jnuv38mhuw3'
}

def catches_404(f):
    @functools.wraps(f)
    def decorated(resp, *args, **kwargs):
        if resp.status_code == 404:
            raise StreamerDoesNotExist
        else:
            return f(resp, *args, **kwargs)
    return decorated

def streamer_status(name):
    @catches_404
    def map_status(resp):
        return resp.json().get('status')

    return moya.Endpoint('https://api.twitch.tv/kraken/channels/{}'
                         .format(name),
                         headers=client_id_header,
                         response_hook=map_status)

def streamer_is_live(streamer_name):
    @catches_404
    def map_is_live(resp):
        # a streamer is live iff the json response's 'stream' key is not None
        return not resp.json().get('stream') == None

    return moya.Endpoint('https://api.twitch.tv/kraken/streams/{}'
                         .format(streamer_name),
                         headers=client_id_header,
                         response_hook=map_is_live)
