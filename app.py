import os
import flask
import peewee
import apns
import utils
import moya

APP_DIR = os.path.dirname(os.path.realpath(__file__))
DATABASE = 'sqliteext:///{}'.format(os.path.join(APP_DIR, 'stitch.db'))
DEBUG = True

app = flask.Flask(__name__)
app.config.from_object(__name__)

import endpoints
import model

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

    return "ok!", 200

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

@app.route('/status', methods=['GET', 'POST'])
# accepts either a streamer_name in the query of a get request, or the
# streamer_names list in the body of a post request
@utils.accepts_parameters('streamer_name')
@utils.accepts_list_parameters('streamer_names')
def status(streamer_name, streamer_names):
    # return a single streamer status
    if streamer_name:
        try:
            streamer = model.Streamer.get(name=streamer_name)
            return flask.jsonify(streamer.serialized)
        except model.Streamer.DoesNotExist:
            return "shit", 400

    # return multiple streamer statuses
    elif streamer_names:
        streamers = []
        for streamer_name in streamer_names:
            try:
                streamers.append(model.Streamer.get(name=streamer_name))
            except model.Streamer.DoesNotExist:
                continue
        return flask.jsonify({ streamer.name: streamer.serialized for streamer in streamers })

    # bad api use
    else:
        return "you suck"

@app.route('/following')
@utils.needs_parameters('apns_token')
def following(apns_token):
    # query all links for this apns_token
    query = (model.Link
             .select()
             .join(model.Device)
             .where(model.Device.apns_token == apns_token))

    streamers = [l.streamer for l in query]
    return flask.jsonify({ streamer.name: streamer.serialized for streamer in streamers })

if __name__ == '__main__':
    model.create_tables()
    app.run(debug=True)
