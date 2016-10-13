import datetime
import itertools
import operator
import celery
import apns
import moya
import endpoints
import model

app = celery.Celery('tasks', broker='redis://localhost//')
# scheduling
app.conf.update(
    CELERYBEAT_SCHEDULE={
        'update-db-every-minute': {
            'task': 'tasks.update_db',
            'schedule': datetime.timedelta(minutes=1)
        }
    }
)

# helper class for prepping a notification that will target multiple devices
class Notification:
    def __init__(self, payload, expiry=0, priority=10):
        self.payload = payload
        self.expiry = expiry
        self.priority = priority
        self.last_id = 0
        self.frame = apns.Frame()

    def add_target(self, device):
        def next_id():
            self.last_id += 1
            return self.last_id

        self.frame.add_item(device.apns_token,
                            self.payload,
                            next_id(),
                            self.expiry,
                            self.priority)

    def add_targets(self, devices):
        for device in devices:
            self.add_target(device)

    @property
    def target_count(self):
        return self.last_id

# helper function to push a text alert to multiple devices
def push_alert(alert, devices, gateway):
    payload = apns.Payload(alert=alert,
                           sound="default")
    notification = Notification(payload)
    notification.add_targets(devices)

    # push!
    print("{}pushing {} to {} {}{}"
          .format('\033[38;5;208;1m',
                  alert,
                  notification.target_count,
                  'devices' if notification.target_count > 1 else 'device',
                  '\033[0m'))

    gateway.send_notification_multiple(notification.frame)

# push all the things 🚀
@app.task
def update_db():
    print("updating database...")
    # provider we'll use for getting status updates from twitch
    provider = moya.Provider()
    # gateway we'll use for sending push notifications to apns
    apns_gateway = apns.APNs(use_sandbox=True,
                             cert_file='apns/stitch-dev-push-cert.pem',
                             key_file='apns/stitch-dev-push-key.pem',
                             enhanced=True).gateway_server

    # query all links and sort (section) them by streamer
    query = (model.Link
             .select()
             .join(model.Streamer)
             .order_by(model.Streamer.name))

    # group links by streamer
    grouped = itertools.groupby([(l.streamer, l.device) for l in query],
                                operator.itemgetter(0))
    # [(streamer, links)] to [(streamer, devices)]
    grouped = [(streamer, [l[1] for l in links]) for (streamer, links) in grouped]

    for (streamer, devices) in grouped:
        # get updated state from twitch
        status = provider.request(endpoints.streamer_status(streamer.name))
        is_live = provider.request(endpoints.streamer_is_live(streamer.name))
        print("--------------------")
        print("checking {}'s state".format(streamer.name))

        # check and push status change
        if streamer.status != status:
            # update the database
            streamer.status = status
            streamer.save()
            # push notification!
            alert = "{} status change! \"{}\"".format(streamer.name, status)
            push_alert(alert, devices, apns_gateway)
        else:
            print("{} still \"{}\"".format(streamer.name, status))

        # check and push live change
        if streamer.is_live != is_live:
            # update the database
            streamer.is_live = is_live
            streamer.save()
            # push notification!
            alert = ("{} went {}!"
                     .format(streamer.name,
                             "live" if is_live else "offline"))
            push_alert(alert, devices, apns_gateway)
        else:
            print("{} still {}"
                  .format(streamer.name,
                          "live" if is_live else "offline"))
