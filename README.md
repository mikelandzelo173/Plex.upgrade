Plex.upgrade
============

Plex.upgrade is a simple script that lets you log into your Plex account and select a playlist to upgrade.

Currently, Python 3.7+ is supported.

## Quickstart

1. Make sure [pip](https://pip.pypa.io/en/stable/installation/) is installed on your machine.

2. Create a virtual environment and activate it (optional), e.g.:
```bash
pip install virtualenv
python3 -m venv venv
source venv/bin/activate
```

3. Install the packages from the `requirements.txt` file using pip:
```bash
pip install -r requirements.txt
```

4. Execute the script and follow the guidance
```bash
./plex_upgrade.py
```

## Example usage

```bash
(venv) ➜ Plex.upgrade ./plex_upgrade.py

  0: PlexServerHome
  1: NAS1337
  2: Another Storage Resource

Select resource to connect to: 1

  0: Favorite music
  1: Random hits
  2: X-mas songs

Select a playlist to upgrade: 0

Do you want to perform a dry run instead of actually modifying anything? [yN]

Do you want to enable the simple replacement mode (The best version available will automatically be selected)? [yN]

Do you want to create a duplicated playlist instead of modifying the selected one? [yN]

✅ Electronic - Tighten Up (2013 Remaster) [mp3] [320]
❌ Sisqó - Thong Song (Unleash the Dragon) [mp3] [160] must be upgraded.

  0: Sisqó - Thong Song (Mr Music Hits 2000 Vol. 9) [flac] [952]
  1: Sisqó - Thong Song (Now That's What I Call Music! 45) [mp3] [320]

Select replacement track (No input so as not to make any changes): 1
🆕 Sisqó - Thong Song (Mr Music Hits 2000 Vol. 9) [flac] [952] will be used instead.

The following tracks were removed:
❌ Sisqó - Thong Song (Unleash the Dragon) [mp3] [160]

The following tracks were added:
🆕 Sisqó - Thong Song (Mr Music Hits 2000 Vol. 9) [flac] [952]

Successfully upgraded playlist Favorite music.
```

A dry run will basically check every track and automatically select a potential replacement track for you. However,
it may be possible that the replacement track is something completely different as it's the highest quality track
as returned by the library search.

As mentioned above, please use the simple replacement mode with caution as it may not work as expected. Use the dry
run to check if it's good for you.

You can also clone the playlist first and all the changes are only applied to the cloned playlist.

## Configuration options

To skip the initial login process every time you use the script you might want to take a note of your authentication
token after your first login and save it to the config.ini file which should be located in `~/.config/plexapi/`
(which can be overridden by setting the environment variable `PLEXAPI_CONFIG_PATH` with the file path you desire) or in
the same directory as this script. Instead of the token you could also save your username and password to the
`config.ini` file.

Instead of the token you could also save your username and password to the `config.ini` file.

```ini
[auth]
myplex_username = JohnDoe
myplex_password = MyR4nd0mPassword
server_token = AjsUeO6Bk89BQPdu5Dnj
```

**Important note for 2FA accounts**  
If you have activated two-factor authentication, after you have already logged in once you can either log in again with
your previously generated token or add your 6-digit number from the authenticator app at the end of your password, e.g.

Authenticator app shows: 123456  
Username: JohnDoe  
Password (will not be echoed): MyR4nd0mPassword123456

Or use the `config.ini` file with your previously generated token:

```ini
[auth]
server_token = AjsUeO6Bk89BQPdu5Dnj
```
