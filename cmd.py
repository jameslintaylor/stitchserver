import sys
import click
import peewee
import model
import moya
import endpoints

@click.group(chain=True)
def cli():
    pass

@cli.command('e-off')
def everyone_offline():
    """everyone offline!"""
    for streamer in model.Streamer.select():
        streamer.is_live = False
        streamer.save()

# everyone offline!
@cli.command('e-on')
def everyone_online():
    """everyone online!"""
    for streamer in model.Streamer.select():
        streamer.is_live = True
        streamer.save()

@cli.command('e-nostat')
def everyone_no_status():
    """everyone get's empty ("") status"""
    for streamer in model.Streamer.select():
        streamer.status = ""
        streamer.save()

@cli.command('link')
@click.option('--apns-token', '-t')
@click.option('--streamer-name', '-n')
def link(apns_token, streamer_name):
    """create a new link"""
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
            print("streamer doesn't exist!")
            return

    device = model.Device.get_or_create(apns_token=apns_token)[0]

    try:
        model.Link.create(streamer=streamer,
                          device=device)
    except peewee.IntegrityError:
        print("link already exists!")
        return

    print("ok!")

@cli.command('unlink')
@click.option('--apns-token', '-t')
@click.option('--streamer-name', '-n')
def link(apns_token, streamer_name):
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
        print("link doesn't exist!")

    link.delete_instance()
    print("ok!")

if __name__ == '__main__':
    cli()
