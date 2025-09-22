#!/usr/bin/env python

"""A simple script that lets you log into your Plex account and select a playlist to upgrade.

URL: https://github.com/mikelandzelo173/Plex.upgrade
Python Version: 3.7+

Disclaimer:
I'm not responsible for any data loss which might occur. There may also be bugs or unexpected behaviors.
Always use with common sense.

What does it do:
You will be prompted to log into your Plex account. After that you can select a playlist that you want to upgrade.
Plex lacks this feature, so I made this script. It comes in handy if you want to find low quality tracks in a gigantic
music playlist or just want to have everything upgraded to a better quality.

Before use:
You will be guided through the whole process but to skip the initial login process every time you use the script you
might want to take a note of your authentication token and save it to the config.ini file which should be located in
~/.config/plexapi/ (which can be overridden by setting the environment variable PLEXAPI_CONFIG_PATH with the file path
you desire) or in the same directory as this script. You could also save your username and password to the config.ini
file instead.

In step 2 you will have to select a resource which is connected to your Plex account. You can only select Plex Media
Servers that host playlists. If there is only one Plex Media Server available, this step will be skipped.

After that, you must select a playlist to upgrade. Please note that smart playlists must not be altered and therefore
are not listed. You can also determine if you want to edit the selected playlist or create a new one based on
the playlist you just selected.

For more information on the Python PlexAPI visit:
https://python-plexapi.readthedocs.io/en/latest/index.html
"""

import os
import random
import re
import subprocess
import sys
from getpass import getpass

from plexapi import PlexConfig
from plexapi.audio import Audio
from plexapi.exceptions import Unauthorized
from plexapi.myplex import MyPlexAccount, MyPlexResource
from plexapi.playlist import Playlist
from plexapi.server import PlexServer
from plexapi.utils import choose

__author__ = "Michael Pölzl"
__copyright__ = "Copyright 2023, Michael Pölzl"
__credits__ = ""
__license__ = "GPL"
__version__ = "1.4.0"
__maintainer__ = "Michael Pölzl"
__email__ = "michael.poelzl@proton.me"
__status__ = "Production"


def duration_to_str(duration: int) -> str:
    """
    Function: duration_to_str()

    Converts a duration value in milliseconds to a usual string representation for audio length.

    :param duration: Duration in milliseconds
    :type duration: int
    :returns: String representation of duration
    :rtype: str
    """

    seconds, milliseconds = divmod(duration, 1000)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def artist(item: Audio) -> str:
    """
    Function: artist()

    Extracts the artist from an Audio object and returns the value as a human readable string representation.
    If no artist is found the album artist will be used instead.

    :param item: Audio object representing a track
    :type item: Audio
    :returns: String representation of the track artist
    :rtype: str
    """

    return item.originalTitle or item.grandparentTitle


def audio_to_str(item: Audio) -> str:
    """
    Function: audio_to_str()

    Converts an Audio object to a human readable string representation.

    :param item: Audio object representing a track
    :type item: Audio
    :returns: String representation of an Audio object
    :rtype: str
    """

    return (
        f"{artist(item)} - {item.title} ({item.album().title}) "
        f"[{duration_to_str(item.media[0].duration)}][{item.media[0].audioCodec}][{item.media[0].bitrate}]"
    )


def choose_continue() -> bool:
    """
    Function: choose_continue()

    Decide on upgrading another playlist.

    :returns: A boolean
    :rtype: bool
    """

    print()

    while True:
        continue_upgrading = input("Do you want to upgrade another playlist? [Yn]")

        if not continue_upgrading or continue_upgrading.lower() == "y":
            return True
        elif continue_upgrading.lower() == "n":
            return False


def choose_duplication() -> bool:
    """
    Function: choose_duplication()

    Decide on duplicating the selected playlist.

    :returns: A boolean
    :rtype: bool
    """

    print()

    while True:
        duplicate = input("Do you want to create a duplicated playlist instead of modifying the selected one? [yN]")

        if duplicate.lower() == "y":
            return True
        elif not duplicate or duplicate.lower() == "n":
            return False


def choose_dry_run() -> bool:
    """
    Function: choose_dry_run()

    Decide on wheter actions should ony be dry runs.

    :returns: A boolean
    :rtype: bool
    """

    print()

    while True:
        dry_run = input("Do you want to perform a dry run instead of actually modifying anything? [yN]")

        if dry_run.lower() == "y":
            return True
        elif not dry_run or dry_run.lower() == "n":
            return False


def choose_simple_replacement_mode() -> bool:
    """
    Function: choose_simple_replacement_mode()

    Decide on wheter a track should be replaced with the best version available or by manually selecting a replacement track.

    :returns: A boolean
    :rtype: bool
    """

    print()

    while True:
        simple_mode = input(
            "Do you want to enable the simple replacement mode (The best version available will automatically be selected)? [yN]",
        )

        if simple_mode.lower() == "y":
            return True
        elif not simple_mode or simple_mode.lower() == "n":
            return False


def choose_spotdl_download() -> bool:
    """
    Function: choose_spotdl_download()

    Decide on wheter tracks which could not be upgraded should be downloaded via spotdl.
    Project and source code: https://github.com/spotDL/spotify-downloader
    Documentation for your custom configuration file: https://spotdl.readthedocs.io/en/latest/usage/#config-file

    :returns: A boolean
    :rtype: bool
    """

    print()

    while True:
        spotdl_download = input(
            "Do you want to download tracks that could not be upgraded within your library with spotdl? [yN]",
        )

        if spotdl_download.lower() == "y":
            return True
        elif not spotdl_download or spotdl_download.lower() == "n":
            return False


def check_quality_requirements(item: Audio) -> bool:
    """
    Function: check_quality_requirements()

    Checks if the quality requirements of a track have been met.

    :param item: Audio object representing the track to check
    :type item: Audio
    :returns: A boolean
    :rtype: bool
    """

    if bool(config.get("upgrade.force_all")):
        return False

    if bool(config.get("upgrade.force_lossless")):
        return item.media[0].audioCodec in [
            "alac",
            "flac",
        ]

    return not (
        item.media[0].audioCodec == "mp3"
        and item.media[0].bitrate < 320
        or item.media[0].audioCodec == "aac"
        and item.media[0].bitrate < 256
    )


def get_account(config: PlexConfig) -> MyPlexAccount:
    """
    Function: get_account()

    Handles the Plex login process and returns a MyPlexAccount object.
    Login is handled via input prompt of username and password or by reading the config.ini file and extracting
    username and password or authentication token from there.

    :param config: PlexConfig object
    :type config: PlexConfig
    :returns: A MyPlexAccount object
    :rtype: MyPlexAccount
    """

    if config.get("auth.server_token"):
        try:
            return MyPlexAccount(token=config.get("auth.server_token"))
        except Exception:
            print("ERROR: Invalid token.")

    if config.get("auth.myplex_username") and config.get("auth.myplex_password"):
        try:
            account = MyPlexAccount(config.get("auth.myplex_username"), config.get("auth.myplex_password"))
            print(f"Your authentication token: {account.authenticationToken}")
            return account
        except Unauthorized:
            print("ERROR: Invalid email, username, or password. Please try again.")
        except Exception:
            print("ERROR: Please try again.")

    while True:
        print("Please provide your login credentials for your Plex account")
        username = input("Username: ")
        password = getpass("Password (will not be echoed): ")

        try:
            account = MyPlexAccount(username, password)
            print(f"Your authentication token: {account.authenticationToken}")
            return account
        except Unauthorized:
            print("ERROR: Invalid email, username, or password. Please try again.")
        except Exception:
            print("ERROR: Please try again.")


def get_config() -> PlexConfig:
    """
    Function: get_config()

    Checks for a config file in either the same directory as this script or in the default configuration path set via
    PLEXAPI_CONFIG_PATH in your environment.

    :returns: A PlexConfig object
    :rtype: PlexConfig
    """

    script_path = os.path.abspath(os.path.dirname(__file__))
    local_config_file = os.path.join(script_path, "config.ini")
    if os.path.exists(local_config_file):
        return PlexConfig(os.path.expanduser(local_config_file))
    else:
        return PlexConfig(os.environ.get("PLEXAPI_CONFIG_PATH", os.path.expanduser("config.ini")))


def get_playlists(server: PlexServer) -> list[Playlist]:
    """
    Function: get_playlists()

    Returns all playlists from a connected resource, filtered by smart status.

    :param server: PlexServer object
    :type server: PlexServer
    :returns: A list of Playlist objects
    :rtype: list[Playlist]
    """

    return [playlist for playlist in server.playlists() if not playlist.smart and playlist.playlistType == "audio"]


def get_resources(account: MyPlexAccount) -> list[MyPlexResource]:
    """
    Function: get_resources()

    Returns all resources connected to a MyPlexAccount, filtered by type. Only "Plex Media Server" items are returned.

    :param account: MyPlexAccount object
    :type account: MyPlexAccount
    :returns: A list of MyPlexResource objects
    :rtype: list[MyPlexResource]
    """

    return [resource for resource in account.resources() if resource.product == "Plex Media Server"]


def upgrade_playlist(
    config: PlexConfig,
    server: PlexServer,
    playlist: Playlist,
    duplicate: bool = False,
    simple_mode: bool = False,
    dry: bool = False,
) -> Playlist:
    """
    Function: upgrade_playlist()

    Upgrades tracks in a playlist to a better version of the same track present in your library.
    Tracks to be upgradeable are as defined in check_quality_requirements().

    :param config: PlexConfig object
    :type config: PlexConfig
    :param server: PlexServer object
    :type server: PlexServer
    :param playlist: Playlist object
    :type playlist: Playlistobject
    :param duplicate: Whether you want to create a duplicated playlist instead of modifying the selected one
    :type duplicate: bool
    :param simple_mode: Whether you want to enable the simple replacement mode
    :type simple_mode: bool
    :param dry: Whether you want to perform a dry run and only check what would be replaced instead of actually
                modifying anything
    :type dry: bool
    :returns: A Playlist object, either the modified or a newly created one
    :rtype: Playlist
    """

    # Get all items
    items = playlist.items()

    # Create a new playlist with the same items for now
    if duplicate and not dry:
        new_playlist = Playlist.create(
            server=server,
            title=f"Copy of {playlist.title}",
            summary=playlist.summary,
            items=items,
            playlistType=playlist.playlistType,
        )

        print(f"Successfully created playlist {new_playlist.title}.")

        playlist = new_playlist
        items = playlist.items()

    items_to_remove = []
    items_to_add = []
    items_ommited = []

    print()

    # Analyze all tracks in the playlist and check if they fail to meet the quality requirements
    for item in items:
        if not check_quality_requirements(item):
            print(f"❌ {audio_to_str(item)} must be upgraded.")

            # Search for the same track in your library
            search_results = server.library.search(
                title=re.sub(r"[^\w\s]", "", item.title),
                artist=re.sub(r"[^\w\s]", "", artist(item)),
                libtype="track",
            )

            # Remove all tracks with lower quality
            replacements = [r for r in search_results if r.media[0].bitrate and r.media[0].bitrate > item.media[0].bitrate]

            # Remove all tracks where there's a completely different artist
            replacements = [r for r in replacements if artist(item).casefold() in artist(r).casefold()]

            # Sort the search results by bitrate and artist
            replacements = sorted(
                replacements,
                key=lambda x: getattr(x, "originalTitle")
                if getattr(x, "originalTitle") is not None
                else getattr(x, "grandparentTitle"),
            )
            replacements = sorted(replacements, key=lambda x: x.media[0].bitrate, reverse=True)

            if not len(replacements):
                items_ommited.append(item)
                print("❔ No potential replacement tracks found. No changes to the track will be made.")
                continue

            replacement_candidate = False

            # Simple replacement mode
            if simple_mode:
                # Automatically select the track with the highest bitrate as the replacement track
                replacement = replacements[0]
                print(f"🆕 {audio_to_str(replacement)} will be used instead.")

                # Add the tracks to separate lists for future usage
                items_to_add.append(replacement)
                items_to_remove.append(item)

                replacement_candidate = True
                continue

            # Manual replacement mode
            else:
                # List all tracks with higher bitrates
                print()
                for index, choice in enumerate(replacements):
                    print(f"  {index}: {audio_to_str(choice)}")
                print()

                while True:
                    try:
                        # Get user choice
                        index = input("Select replacement track (No input so as not to make any changes): ")

                        # Add the tracks to separate lists for future usage
                        if index:
                            replacement = replacements[int(index)]
                            items_to_add.append(replacement)
                            items_to_remove.append(item)
                            replacement_candidate = True

                            print(f"🆕 {audio_to_str(replacement)} will be used instead.")

                        break
                    except (ValueError, IndexError):
                        pass

            # Check if similar tracks have been found
            if not replacement_candidate:
                items_ommited.append(item)

                if simple_mode:
                    print("❔ No replacement track found. No changes to the track will be made.")
                else:
                    print("❔ No replacement track selected. No changes to the track will be made.")

        else:
            print(f"✅ {audio_to_str(item)}")

    print()

    # Perform all modifications
    if not dry:
        # Remove all items to be upgraded
        if len(items_to_remove):
            playlist.removeItems(items_to_remove)
            print("The following tracks were removed:")
            for item in items_to_remove:
                print(f"❌ {audio_to_str(item)}")
            print()

        # Add new items with better quality
        if len(items_to_add):
            playlist.addItems(items_to_add)
            print("The following tracks were added:")
            for item in items_to_add:
                print(f"🆕 {audio_to_str(item)}")
            print()

        # List all items which couldn't be upgraded
        if len(items_ommited):
            print("The following tracks couldn't be upgraded:")
            for item in items_ommited:
                print(f"❔ {audio_to_str(item)}")
            print()

        print(f"Successfully upgraded playlist {playlist.title}.")

        # Download tracks that couldn't be upgraded with spotdl
        if choose_spotdl_download():
            script_path = os.path.dirname(os.path.abspath(__file__))

            subprocess.run(["pip", "install", "spotdl", "--upgrade"])
            os.makedirs("spotdl", exist_ok=True)
            os.chdir(os.path.join(script_path, "spotdl"))

            print()
            for item in items_ommited:
                print(f"Searching for {artist(item)} - {item.title}")
                subprocess.run(["spotdl", "download", f"{artist(item)} - {item.title}"])

            os.chdir(script_path)

            print("Done downloading tracks.")

    return playlist


if __name__ == "__main__":
    # Load configuration
    config = get_config()

    # Login to the Plex account
    account = get_account(config)

    # Select a resource to connect to
    resources = get_resources(account)
    resource = choose("Select resource to connect to", resources, "name")

    # Connect to the selected resource and create a server object
    server = account.resource(resource.name).connect()

    while True:
        # Select a playlist to upgrade
        playlists = get_playlists(server)
        playlist = choose("Select a playlist to upgrade", playlists, "title")

        # Decide on wheter this should only be a dry run
        dry = choose_dry_run()

        # Decide on wheter the simple replacement mode should be used
        simple_mode = True if dry else choose_simple_replacement_mode()

        # Decide on duplicating the selected playlist
        duplicate = False if dry else choose_duplication()

        # Upgrade playlist
        upgrade_playlist(
            config=config,
            server=server,
            playlist=playlist,
            duplicate=duplicate,
            simple_mode=simple_mode,
            dry=dry,
        )

        if not choose_continue():
            sys.exit()
