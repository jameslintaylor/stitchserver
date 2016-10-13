import os
import flask
import peewee
import apns
import model
import utils
import moya
import endpoints

APP_DIR = os.path.dirname(os.path.realpath(__file__))
DATABASE = 'sqliteext:///{}'.format(os.path.join(APP_DIR, 'stitch.db'))
DEBUG = True

app = flask.Flask(__name__)
app.config.from_object(__name__)

@app.route('/link', methods=['POST'])
@utils.needs_parameters('apns_token', 'streamer_name')
def link(apns_token, streamer_name):
    try:
        streamer = model.Streamer.get(name=streamer_name)

    except model.Streamer.DoesNotExist:
        provider = moya.Provider()
        try:
            status = provider.request(endpoints.streamer_status(streamer_name))
            is_live = provider.request(endpoints.streamer_is_live(streamer_name))
            streamer = model.Streamer.create(name=streamer_name,
                                             status=status,
                                             is_live=is_live)
        except endpoints.StreamerDoesNotExist:
            return "streamer doesn't exist!", 400

    device = model.Device.get_or_create(apns_token=apns_token)[0]

    try:
        model.Link.create(streamer=streamer,
                          device=device)
    except peewee.IntegrityError:
        return "link already exists!", 400

    return "ok!"

@app.route('/unlink', methods=['POST'])
@utils.needs_parameters('apns_token', 'streamer_name')
def unlink(apns_token, streamer_name):
    try:
        link = (model.Link
                .select(model.Link)
                .join(model.Streamer)
                .switch(model.Link)
                .join(model.Device)
                .where((model.Streamer.name == streamer_name) &
                       (model.Device.apns_token == apns_token))
                .get())

    except model.Link.DoesNotExist:
        return "link doesn't exist!", 400

    link.delete_instance()
    return "ok!"

if __name__ == '__main__':
    model.create_tables()
    app.run(host='0.0.0.0', debug=True)
