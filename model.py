import peewee
import playhouse.flask_utils
import app

flask_db = playhouse.flask_utils.FlaskDB(app.app)
db = flask_db.database

class Streamer(flask_db.Model):
    name = peewee.CharField(unique=True)
    # the text status of the streamer (ie. 'be back in an hour!')
    status = peewee.TextField()
    # the streamer's stream status (live or offline)
    is_live = peewee.BooleanField()

    @property
    def serialized(self):
        return {
            'name': self.name,
            'status': self.status,
            'is_live': self.is_live
        }

class Device(flask_db.Model):
    apns_token = peewee.CharField(unique=True)

# many to many intermediary table between streamers and linked devices
class Link(flask_db.Model):
    streamer = peewee.ForeignKeyField(Streamer)
    device = peewee.ForeignKeyField(Device)
    # takes the form "{streamer.name} {device.apns_token}" to prevent
    # duplicate links
    compositeKey = peewee.CharField(unique=True)

    def save(self, *args, **kwargs):
        # generate the composite key using a whitespace delimiter (whitespace
        # isn't valid in either a twitch channel name or an apns token)
        self.compositeKey = '{} {}'.format(self.streamer.name, self.device.apns_token)
        return super(Link, self).save(*args, **kwargs)

def create_tables():
    db.create_tables([Streamer, Device, Link], safe=True)
