# Miro - an RSS based video player application
# Copyright (C) 2005-2009 Participatory Culture Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the OpenSSL
# library.
#
# You must obey the GNU General Public License in all respects for all of
# the code used other than OpenSSL. If you modify file(s) with this
# exception, you may extend this exception to your version of the file(s),
# but you are not obligated to do so. If you do not wish to do so, delete
# this exception statement from your version. If you delete this exception
# statement from all source files in the program, then also delete it here.

"""messages.py -- Message passing between the frontend thread and the backend
thread.

The backend thread is the eventloop, which processes things like feed updates
and handles reading and writing to the database.  The frontend thread is the
thread of the UI toolkit we're using.  Communication between the two threads
is handled by passing messages between the two.  These messages are handled
asynchronously.

This module defines the messages that are passed between the two threads.
"""

import logging
import re
import urlparse

from miro.gtcache import gettext as _
from miro.folder import ChannelFolder, PlaylistFolder
from miro.plat import resources
from miro import util, prefs

class MessageHandler(object):
    def __init__(self):
        self.message_map = {} # maps message classes to method names
        self.complained_about = set()

    def call_handler(self, method, message):
        """Arrange for a message handler method to be called in the correct
        thread.  Must be implemented by subclasses.
        """
        raise NotImplementedError()

    def handle(self, message):
        handler_name = self.get_message_handler_name(message)
        try:
            handler = getattr(self, handler_name)
        except AttributeError:
            if handler_name not in self.complained_about:
                logging.warn("MessageHandler doesn't have a %s method "
                        "to handle the %s message" % (handler_name,
                            message.__class__))
                self.complained_about.add(handler_name)
        else:
            self.call_handler(handler, message)

    def get_message_handler_name(self, message):
        try:
            return self.message_map[message.__class__]
        except KeyError:
            self.message_map[message.__class__] = \
                    self.calc_message_handler_name(message.__class__)
            return self.message_map[message.__class__]

    def calc_message_handler_name(self, message_class):
        def replace(match):
            return '%s_%s' % (match.group(1), match.group(2).lower())
        underscores = re.sub(r'([a-z])([A-Z])', replace,
                message_class.__name__)
        return 'handle_' + underscores.lower()


class Message(object):
    """Base class for all Messages."""

    @classmethod
    def install_handler(cls, handler):
        """Install a new message handler for this class.  When
        send_to_frontend() or send_to_backend() is called, this handler will
        be invoked.
        """
        cls.handler = handler

class BackendMessage(Message):
    """Base class for Messages that get sent to the backend."""

    def send_to_backend(self):
        try:
            handler = self.handler
        except AttributeError:
            logging.warn("No handler for backend messages")
        else:
            handler.handle(self)

class FrontendMessage(Message):
    """Base class for Messages that get sent to the frontend."""

    def send_to_frontend(self):
        try:
            handler = self.handler
        except AttributeError:
            logging.warn("No handler for frontend messages")
        else:
            handler.handle(self)

# Backend Messages

class FrontendStarted(BackendMessage):
    """Inform the backend that the frontend has finished starting up."""
    pass

class TrackChannels(BackendMessage):
    """Begin tracking channels.

    After this message is sent, the backend will send back a ChannelList
    message, then it will send ChannelsChanged messages whenever the channel
    list changes.
    """
    pass

class StopTrackingChannels(BackendMessage):
    """Stop tracking channels."""
    pass

class QuerySearchInfo(BackendMessage):
    """Ask the backend to send a CurrentSearchInfo message.  """
    pass

class TrackPlaylists(BackendMessage):
    """Begin tracking playlists.

    After this message is sent, the backend will send back a PlaylistList
    message, then it will send PlaylistsChanged messages whenever the list of
    playlists changes.
    """
    pass

class StopTrackingPlaylists(BackendMessage):
    """Stop tracking playlists."""
    pass

class TrackGuides(BackendMessage):
    """Begin tracking guides.

    After this message is sent, the backend will send back a GuideList
    message, then it will send GuidesChanged messages whenever the guide
    list changes.
    """
    pass

class StopTrackingGuides(BackendMessage):
    """Stop tracking guides."""
    pass

class TrackItems(BackendMessage):
    """Begin tracking items for a feed

    After this message is sent, the backend will send back a ItemList message,
    then it will send ItemsChanged messages for items in the feed.

    type is the type of object that we are tracking items for.  It can be one
    of the following:

    'feed' -- Items in a feed
    'playlist' - Items in a playlist
    'new' -- Items that haven't been watched
    'downloading' -- Items being downloaded
    'library' -- All items

    id should be the id of a feed/playlist. For new, downloading and library
    it is ignored.
    """

    def __init__(self, type, id):
        self.type = type
        self.id = id

class TrackItemsManually(BackendMessage):
    """Track a manually specified list of items.

    ItemList and ItemsChanged messages will have "manual" as the type and
    will use the id specified in the constructed.
    """

    def __init__(self, id, ids_to_track):
        self.id = id
        self.ids_to_track = ids_to_track
        self.type = 'manual'

class StopTrackingItems(BackendMessage):
    """Stop tracking items for a feed."""

    def __init__(self, type, id):
        self.type = type
        self.id = id

class TrackDownloadCount(BackendMessage):
    """Start tracking the number of downloading items.  After this message is
    received the backend will send a corresponding DownloadCountChanged
    message.  It will also send DownloadCountChanged whenever the count
    changes.
    """
    pass

class StopTrackingDownloadCount(BackendMessage):
    """Stop tracking the download count."""
    pass

class TrackPausedCount(BackendMessage):
    """Start tracking the number of paused downloading items.  After this
    message is received, the backend will send a corresponding PausedCountChanged
    message.  It will also send PausedCountChanged whenever the count
    changes.
    """
    pass

class StopTrackingPausedCount(BackendMessage):
    """Stop tracking the paused count."""
    pass

class TrackNewCount(BackendMessage):
    """Start tracking the number of new videos.  When this message is received
    the backend will send a corresponding NewCountChanged message.  It will
    also send NewCountChanged whenever the count changes.
    """
    pass

class StopTrackingNewCount(BackendMessage):
    """Stop tracking the new videos count."""
    pass

class TrackUnwatchedCount(BackendMessage):
    """Start tracking the number of unwatched items.  When this message is
    received, the backend will send a corresponding UnwatchedCountChanged
    message.  It will also send UnwatchedCountChanged whenever the count changes.
    """
    pass

class StopTrackingUnwatchedCount(BackendMessage):
    """Stop tracking the unwatched items count."""
    pass

class TrackWatchedFolders(BackendMessage):
    """Begin tracking watched folders

    After this message is sent, the backend will send back a WatchedFolderList
    message, then it will send WatchedFoldersChanged messages whenever the
    list changes.
    """
    pass

class StopTrackingWatchedFolders(BackendMessage):
    """Stop tracking watched folders."""
    pass

class SetFeedExpire(BackendMessage):
    """Sets the expiration for a feed."""
    def __init__(self, channel_info, expire_type, expire_time):
        self.channel_info = channel_info
        self.expire_type = expire_type
        self.expire_time = expire_time

class SetFeedMaxNew(BackendMessage):
    """Sets the feed's max new property."""
    def __init__(self, channel_info, max_new):
        self.channel_info = channel_info
        self.max_new = max_new

class SetFeedMaxOldItems(BackendMessage):
    """Sets the feed's max old items property."""
    def __init__(self, channel_info, max_old_items):
        self.channel_info = channel_info
        self.max_old_items = max_old_items

class CleanFeed(BackendMessage):
    """Tells the backend to clean the old items from a feed.
    """
    def __init__(self, channel_id):
        self.channel_id = channel_id

class ImportFeeds(BackendMessage):
    """Tell the backend to import feeds from an .opml file.

    Attributes:
    filename -- file name that exists
    """
    def __init__(self, filename):
        self.filename = filename

class ExportSubscriptions(BackendMessage):
    """Tell the backend to export subscriptions to an .opml file.

    Attributes:
    filename -- file name to export to
    """
    def __init__(self, filename):
        self.filename = filename

class RenameObject(BackendMessage):
    """Tell the backend to rename a feed/playlist/folder.
    
    Attributes:
    type -- 'feed', 'playlist', 'feed-folder' or 'playlist-folder'
    id  -- id of the object to rename
    new_name -- new name for the object
    """
    def __init__(self, type, id, new_name):
        self.type = type
        self.id = id
        self.new_name = util.toUni(new_name)

class UpdateFeed(BackendMessage):
    """Updates a feed."""
    def __init__(self, id):
        self.id = id

class UpdateFeedFolder(BackendMessage):
    """Updates the feeds in a feed folder."""
    def __init__(self, id):
        self.id = id

class MarkFeedSeen(BackendMessage):
    """Mark a feed as seen"""
    def __init__(self, id):
        self.id = id

class MarkItemWatched(BackendMessage):
    """Mark an item as watched"""
    def __init__(self, id):
        self.id = id

class MarkItemUnwatched(BackendMessage):
    """Mark an item as unwatched"""
    def __init__(self, id):
        self.id = id

class SetItemResumeTime(BackendMessage):
    """Set an item resume time"""
    def __init__(self, id, time):
        self.id = id
        self.resume_time = time

class UpdateAllFeeds(BackendMessage):
    """Updates all feeds."""
    pass

class DeleteFeed(BackendMessage):
    """Delete a feed."""
    def __init__(self, id, is_folder, keep_items):
        self.id = id
        self.is_folder = is_folder
        self.keep_items = keep_items

class DeleteWatchedFolder(BackendMessage):
    """Delete a watched folder.

    NOTE: this separate from DeleteFeed since not all watched folders are
    visible.
    """
    def __init__(self, id):
        self.id = id

class DeletePlaylist(BackendMessage):
    """Delete a playlist."""
    def __init__(self, id, is_folder):
        self.id = id
        self.is_folder = is_folder

class DeleteSite(BackendMessage):
    """Delete an external channel guide."""
    def __init__(self, id):
        self.id = id

class NewGuide(BackendMessage):
    """Create a new channel guide.
    """
    def __init__(self, url):
        self.url = util.toUni(url)

class NewFeed(BackendMessage):
    """Creates a new feed."""
    def __init__(self, url, section=u"video"):
        self.url = util.toUni(url)
        self.section = section

class NewFeedSearchFeed(BackendMessage):
    """Creates a new feed based on a search through a feed."""
    def __init__(self, channel_info, search_term, section=u"video"):
        self.channel_info = channel_info
        self.search_term = search_term
        self.section = section

class NewFeedSearchEngine(BackendMessage):
    """Creates a new feed from a search engine."""
    def __init__(self, search_engine_info, search_term, section=u"video"):
        self.search_engine_info = search_engine_info
        self.search_term = search_term
        self.section = section

class NewFeedSearchURL(BackendMessage):
    """Creates a new feed from a url."""
    def __init__(self, url, search_term, section):
        self.url = url
        self.search_term = search_term
        self.section = section

class NewWatchedFolder(BackendMessage):
    """Creates a new watched folder."""
    def __init__(self, path):
        self.path = path

class SetWatchedFolderVisible(BackendMessage):
    """Changes if a watched folder is visible in the tab list or not."""
    def __init__(self, id, visible):
        self.id = id
        self.visible = visible

class NewPlaylist(BackendMessage):
    """Create a new playlist."""
    def __init__(self, name, ids):
        self.name = util.toUni(name)
        self.ids = ids

class NewFeedFolder(BackendMessage):
    """Create a new feed folder."""
    def __init__(self, name, section, child_feed_ids):
        self.name = util.toUni(name)
        self.section = section
        self.child_feed_ids = child_feed_ids

class NewPlaylistFolder(BackendMessage):
    """Create a new playlist folder."""
    def __init__(self, name, child_playlist_ids):
        self.name = util.toUni(name)
        self.child_playlist_ids = child_playlist_ids

class ChangeMoviesDirectory(BackendMessage):
    """Change the current movies directory.

    If migrate is True, then the backend will send a series of
    MigrationProgress messages while the migration happens.
    """
    def __init__(self, path, migrate):
        self.path = path
        self.migrate = migrate

class AddVideosToPlaylist(BackendMessage):
    def __init__(self, playlist_id, video_ids):
        self.playlist_id = playlist_id
        self.video_ids = video_ids

class RemoveVideosFromPlaylist(BackendMessage):
    def __init__(self, playlist_id, video_ids):
        self.playlist_id = playlist_id
        self.video_ids = video_ids

class DownloadURL(BackendMessage):
    def __init__(self, url, handle_unknown_callback=None):
        self.url = util.toUni(url)
        self.handle_unknown_callback = handle_unknown_callback

class OpenIndividualFile(BackendMessage):
    def __init__(self, filename):
        self.filename = filename

class OpenIndividualFiles(BackendMessage):
    def __init__(self, filenames):
        self.filenames = filenames

class AddFiles(BackendMessage):
    """This is like OpenIndividualFiles, but is handled differently
    in that adding files doesn't cause videos that were added to be
    played.
    """
    def __init__(self, filenames):
        self.filenames = filenames

class CheckVersion(BackendMessage):
    def __init__(self, up_to_date_callback):
        self.up_to_date_callback = up_to_date_callback

class Search(BackendMessage):
    """Search a search engine with a search term.
    
    The backend will send a SearchComplete message.
    """
    def __init__(self, searchengine_id, terms):
        self.id = searchengine_id
        self.terms = terms

class StartDownload(BackendMessage):
    """Start downloading an item."""
    def __init__(self, id):
        self.id = id
    def __repr__(self):
        return BackendMessage.__repr__(self) + (", id: %s" % self.id)

class CancelDownload(BackendMessage):
    """Cancel downloading an item."""
    def __init__(self, id):
        self.id = id

class CancelAllDownloads(BackendMessage):
    """Cancels all downloading items."""
    pass

class PauseAllDownloads(BackendMessage):
    """Pauses all downloading items."""
    pass

class PauseDownload(BackendMessage):
    """Pause downloading an item."""
    def __init__(self, id):
        self.id = id

class ResumeAllDownloads(BackendMessage):
    """Resumes all downloading items."""
    pass

class ResumeDownload(BackendMessage):
    """Resume downloading an item."""
    def __init__(self, id):
        self.id = id

class StartUpload(BackendMessage):
    """Start uploading a torrent."""
    def __init__(self, id):
        self.id = id

class StopUpload(BackendMessage):
    """Stop uploading a torrent."""
    def __init__(self, id):
        self.id = id

class KeepVideo(BackendMessage):
    """Cancel the auto-expiration of an item's video"""
    def __init__(self, id):
        self.id = id
    def __repr__(self):
        return BackendMessage.__repr__(self) + (", id: %s" % self.id)

class SaveItemAs(BackendMessage):
    """Saves an item in the dark clutches of Miro to somewhere else."""
    def __init__(self, id, filename):
        self.id = id
        self.filename = filename

class AddItemToLibrary(BackendMessage):
    """Adds an item to the library."""
    def __init__(self, id):
        self.id = id

class RemoveVideoEntry(BackendMessage):
    """Remove the entry for an external video"""
    def __init__(self, id):
        self.id = id

class DeleteVideo(BackendMessage):
    """Delete the video for an item's video"""
    def __init__(self, id):
        self.id = id
    def __repr__(self):
        return BackendMessage.__repr__(self) + (", id: %s" % self.id)

class RenameVideo(BackendMessage):
    """Renames the video"""
    def __init__(self, id, new_name):
        self.id = id
        self.new_name = new_name

class RevertFeedTitle(BackendMessage):
    """Reverts the feed's title back to the original"""
    def __init__(self, id):
        self.id = id

class RevertItemTitle(BackendMessage):
    """Reverts the item's title back to the original"""
    def __init__(self, id):
        self.id = id

class PlayAllUnwatched(BackendMessage):
    """Figures out all the unwatched items and plays them."""
    def __init__(self):
        pass

class FolderExpandedChange(BackendMessage):
    """Inform the backend when a folder gets expanded/collapsed
    """
    def __init__(self, type, id, expanded):
        self.type = type
        self.id = id
        self.expanded = expanded

class AutodownloadChange(BackendMessage):
    """Inform the backend that the user changed the auto-download setting for
    a feed.  The possible setting values are "all", "new" and "off"
    """
    def __init__(self, id, setting):
        self.id = id
        self.setting = setting

class TabsReordered(BackendMessage):
    """Inform the backend when the channel tabs are rearranged.  This includes
    simple position changes and also changes to which folders the channels are
    in.

    Attributes:

    toplevels -- a dictionary of {'type': [channelinfo1, channelinfo2]},
        where 'channelinfo' is a ChannelInfo object without parents

    folder_children -- dict mapping channel folder ids to a list of
        ChannelInfo objects for their children
    """
    def __init__(self):
        self.toplevels = {
            u'feed': [],
            u'audio-feed': [],
            u'playlist': []}
        self.folder_children = {}

    def append(self, info, type):
        self.toplevels[type].append(info)
        if info.is_folder:
            self.folder_children[info.id] = []

    def append_child(self, parent_id, info):
        self.folder_children[parent_id].append(info)

class PlaylistReordered(BackendMessage):
    """Inform the backend when the items in a playlist are re-ordered.

    Attributes:
    id -- playlist that was re-ordered
    item_ids -- List of ids for item in the playlist, in their new order.
    """
    def __init__(self, id, item_ids):
        self.id = id
        self.item_ids = item_ids

class SubscriptionLinkClicked(BackendMessage):
    """Inform the backend that the user clicked on a subscription link in a
    web browser.
    """
    def __init__(self, url):
        self.url = url

class ReportCrash(BackendMessage):
    """Sends a crash report.
    """
    def __init__(self, report, text, send_report):
        self.report = report
        self.text = text
        self.send_report = send_report

class SaveFrontendState(BackendMessage):
    """Save data for the frontend."""
    def __init__(self, list_view_displays, sort_states):
        self.list_view_displays = list_view_displays
        self.sort_states = sort_states

class QueryFrontendState(BackendMessage):
    """Ask for a CurrentFrontendState message to be sent back."""

# Frontend Messages

class StartupSuccess(FrontendMessage):
    """The startup process is complete.  The frontend should wait for this
    signal to show the UI to the user.
    """
    pass

class StartupFailure(FrontendMessage):
    """The startup process failed.  The frontend should inform the user that
    this happened and quit.

    Attributes:
        summary -- Short, user-friendly, summary of the problem
        description -- Longer explanation of the problem
    """

    def __init__(self, summary, description):
        self.summary = summary
        self.description = description

class ChannelInfo(object):
    """Tracks the state of a channel

    Attributes:

    name -- channel name
    url -- channel url (None for channel folders)
    id -- object id
    section -- which section this is in (audio or video)
    tab_icon -- path to this channel's tab icon
    thumbnail -- path to this channel's thumbnail
    num_downloaded -- number of downloaded items in the feed
    unwatched -- number of unwatched videos
    available -- number of newly downloaded videos
    is_folder -- is this a channel folder?
    is_directory_feed -- is this channel is a watched directory?
    parent_id -- id of parent folder or None
    is_updating -- whether or not the feed is currently updating
    has_downloading -- are videos currently being downloaded for this channel?
    base_href -- url to use for relative links for items in this channel.
      This will be None for ChannelFolders.
    autodownload_mode -- current autodownload mode ('all', 'new' or 'off')
    search_term -- the search term used for this feed or None
    expire -- expire type ("system", "never", or "feed")
    expire_time -- expire time in hours
    max_new -- maximum number of items this feed wants
    max_old_items -- maximum number of old items to remember
    """
    def __init__(self, channel_obj):
        self.name = channel_obj.get_title()
        self.id = channel_obj.id
        self.section = channel_obj.section
        self.unwatched = channel_obj.numUnwatched()
        self.available = channel_obj.numAvailable()
        self.has_downloading = channel_obj.hasDownloadingItems()
        if hasattr(channel_obj, "searchTerm"):
            self.search_term = channel_obj.searchTerm
        else:
            self.search_term = None
        if not isinstance(channel_obj, ChannelFolder):
            self.has_original_title = channel_obj.has_original_title()
            self.is_updating = channel_obj.isUpdating()
            self.parent_id = channel_obj.folder_id
            self.url = channel_obj.getURL()
            self.thumbnail = channel_obj.getThumbnailPath()
            self.base_href = channel_obj.getBaseHref()
            self.autodownload_mode = channel_obj.getAutoDownloadMode()
            self.is_folder = False
            self.is_directory_feed = (self.url is not None and
                    self.url.startswith('dtv:directoryfeed'))
            self.tab_icon = channel_obj.getThumbnailPath()
            self.expire = channel_obj.get_expiration_type()
            self.expire_time = channel_obj.get_expiration_time()
            self.max_new = channel_obj.get_max_new()
            self.max_old_items = channel_obj.get_max_old_items()
            self.num_downloaded = channel_obj.num_downloaded()
        else:
            self.is_updating = False
            self.parent_id = None
            self.url = None
            self.thumbnail = resources.path('images/folder-icon.png')
            self.autodownload_mode = self.base_href = None
            self.is_folder = True
            self.tab_icon = resources.path('images/icon-folder.png')
            self.is_directory_feed = False
            self.expire = None
            self.expire_time = None
            self.max_new = None
            self.max_old_items = None
            self.num_downloaded = None

class PlaylistInfo(object):
    """Tracks the state of a playlist

    Attributes:

    name -- playlist name
    id -- object id
    is_folder -- is this a playlist folder?
    """

    def __init__(self, playlist_obj):
        self.name = playlist_obj.get_title()
        self.id = playlist_obj.id
        self.is_folder = isinstance(playlist_obj, PlaylistFolder)
        if self.is_folder:
            self.parent_id = None
        else:
            self.parent_id = playlist_obj.folder_id

class GuideInfo(object):
    """Tracks the state of a channel guide

    Attributes:

    name -- channel name
    id -- object id
    url -- URL for the guide
    allowed_urls -- URLs that should be also considered part of the guide
    default -- is this the default channel guide?
    favicon -- the favicon for the guide
    faviconIsDefault -- true if the guide is using the default site icon and
                        not a favicon from the web
    """
    def __init__(self, guide):
        self.name = guide.get_title()
        self.id = guide.id
        self.url = guide.getURL()
        self.default = guide.getDefault()
        self.allowed_urls = guide.allowedURLs
        self.favicon = guide.get_favicon_path()
        self.faviconIsDefault = not (guide.iconCache and
                                     guide.iconCache.get_filename())

class ItemInfo(object):
    """Tracks the state of an item

    Attributes:

    name -- name of the item
    id -- object id
    feed_id -- id for the items feed
    feed_name -- name of the feed item is attached to
    feed_url -- URL of the feed item is attached to 
    description -- longer description for the item (HTML)
    state -- see Item.get_state()
    release_date -- datetime object when the item was published
    size -- size of the item in bytes
    duration -- length of the video in seconds
    resume_time -- time at which playback should restart
    permalink -- URL to a permalink to the item (or None)
    commentslink -- URL to a comments page for the item (or None)
    payment_link -- URL of the payment page associated with the item
        (or empty string)
    has_sharable_url -- does this item have a sharable URL?
    can_be_saved -- is this an expiring downloaded item?
    downloaded -- has the item been downloaded?
    is_external -- is this item external (true) or from a channel (false)?
    is_single -- is this item a single (true) or not (false)?
    expiration_date -- datetime object for when the item will expire (or None)
    item_viewed -- has the user ever seen the item?
    video_watched -- has the user watched the video for the item?
    video_path -- the file path to the video for this item (or None)
    thumbnail -- path to the thumbnail for this file
    thumbnail_url -- URL for the item's thumbnail (or None)
    file_format -- User-facing format description.  Possibly the file type,
        pulled from the mime_type, or more generic, like "audio"
    license -- this file's license, if known.
    file_type -- filetype of the enclosure that would be downloaded
    file_url -- URL of the enclosure that would be downloaded
    download_info -- DownloadInfo object containing info about the download
        (or None)
    is_container_item -- whether or not this item is actually a
        collection of files as opposed to an individual item
    self.leechers -- (Torrent only) number of leeching clients
    self.seeders -- (Torrent only) number of seeding clients
    self.up_rate -- (Torrent only) how fast we're uploading data
    self.down_rate -- (Torrent only) how fast we're downloading data
    self.up_total -- (Torrent only) total amount we've uploaded
    self.down_total -- (Torrent only) total amount we've downloaded
    """
    def __init__(self, item):
        self.name = item.get_title()
        self.has_original_name = item.has_original_title()
        self.id = item.id
        self.feed_id = item.feed_id
        if item.feed_id:
            feed = item.dd.getObjectByID(self.feed_id)
            self.feed_name = feed.get_title()
            self.feed_url = feed.getURL()
        else:
            self.feed_name = None
            self.feed_url = None
        self.description = item.get_description()
        self.state = item.get_state()
        self.release_date = item.get_release_date_obj()
        self.size = item.get_size()
        self.duration = item.get_duration_value()
        self.resume_time = item.resumeTime
        self.permalink = item.get_link()
        self.commentslink = item.get_comments_link()
        self.payment_link = item.get_payment_link()
        self.has_sharable_url = item.hasSharableURL()
        self.can_be_saved = item.show_save_button()
        self.pending_manual_dl = item.is_pending_manual_download()
        self.pending_auto_dl = item.is_pending_auto_download()
        if not item.keep and not item.is_external():
            self.expiration_date = item.getExpirationTime()
        else:
            self.expiration_date = None
        self.item_viewed = item.get_viewed()
        self.downloaded = item.is_downloaded()
        self.is_external = item.is_external()
        self.is_single = item.is_single()
        self.video_watched = item.getSeen()
        self.video_path = item.get_video_filename()
        self.thumbnail = item.getThumbnail()
        self.thumbnail_url = item.getThumbnailURL()
        self.file_format = item.get_format()
        self.license = item.get_license()
        self.file_url = item.getURL()
        self.is_container_item = item.isContainerItem

        self.file_type = item.enclosure_type
        self.file_url = item.url

        if item.downloader:
            self.download_info = DownloadInfo(item.downloader)
        elif self.state == 'downloading':
            self.download_info = PendingDownloadInfo()
        else:
            self.download_info = None

        ## Torrent-specific stuff
        self.leechers = self.seeders = self.up_rate = None
        self.down_rate = self.up_total = self.down_total = None
        if item.looks_like_torrent() and hasattr(item.downloader, 'status'):
            status = item.downloader.status
            if item.is_transferring():
                # gettorrentdetails only
                self.leechers = status.get('leechers', 0)
                self.seeders = status.get('seeders', 0)
                self.up_rate = status.get('upRate', 0)
                self.down_rate = status.get('rate', 0)

            # gettorrentdetailsfinished & gettorrentdetails
            self.up_total = status.get('uploaded', 0)
            self.down_total = status.get('currentSize', 0)

class DownloadInfo(object):
    """Tracks the download state of an item.

    Attributes:

    downloaded_size -- bytes downloaded
    rate -- current download rate, in bytes per second
    state -- one of 'downloading', 'uploading', 'finished', 'failed' or 
        'paused'.  'uploading' is for torrents only.  It means that we've
        finished downloading the torrent and are now seeding it.
    eta -- Estimated seconds before the download is finished
    startup_activity -- The current stage of starting up
    finished -- True if the item has finished downloading
    torrent -- Is this a Torrent download?
    """
    def __init__(self, downloader):
        self.downloaded_size = downloader.get_current_size()
        self.rate = downloader.getRate()
        self.state = downloader.get_state()
        self.startup_activity = downloader.get_startup_activity()
        self.finished = downloader.isFinished()
        self.torrent = (downloader.getType() == 'bittorrent')
        if self.state == 'failed':
            self.reason_failed = downloader.getReasonFailed()
            self.short_reason_failed = downloader.getShortReasonFailed()
        else:
            self.reason_failed = u""
            self.short_reason_failed = u""
        self.eta = downloader.getETA()

class PendingDownloadInfo(DownloadInfo):
    """DownloadInfo object for pending downloads (downloads queued, but not
    started because we've reached some limit)
    """
    def __init__(self):
        self.downloaded_size = 0
        self.rate = 0
        self.state = 'pending'
        self.startup_activity = _('queued for download')
        self.finished = False
        self.torrent = False
        self.reason_failed = u""
        self.short_reason_failed = u""
        self.eta = 0

class WatchedFolderInfo(object):
    """Tracks the state of a watched folder.
    
    Attributes:

    id -- ID of the channel
    path -- Path to the folder being watched
    visible -- Is the watched folder shown on the tab list?
    """
    def __init__(self, channel):
        self.id = channel.id
        self.path = channel.dir
        self.visible = channel.visible

class GuideList(FrontendMessage):
    """Sends the frontend the initial list of channel guides

    Attributes:
    default_guide -- The Default channel guide
    guides -- list added channel guides
    """

    def __init__(self, guides):
        self.default_guide = [g for g in guides if g.default]
        if len(self.default_guide) == 0:
            # The problem here is that Miro persists guides and it's possible
            # for it to have a default channel guide persisted, but when you
            # set the channel guide via the DTV_CHANNELGUIDE_URL, then there's
            # no default guide.  So we generate one here.  Bug #11027.
            from miro import guide, config, prefs
            cg = guide.ChannelGuide(util.toUni(config.get(prefs.CHANNEL_GUIDE_URL)))
            cg_info = GuideInfo(cg)
            self.default_guide = [cg_info]
        elif len(self.default_guide) > 1:
            logging.warning("Multiple default guides!  Picking the first one.")
            self.default_guide = [self.default_guide[0]]
        self.default_guide = self.default_guide[0]
        self.added_guides = [g for g in guides if not g.default]

class TabList(FrontendMessage):
    """Sends the frontend the current list of channels and playlists

    This is sent at startup and when the changes to the list of
    channels/playlists is too complex to describe with a TabsChanged message.

    Attributes:
    type -- 'feed' or 'playlist'
    toplevels -- the list of ChannelInfo/PlaylistInfo objects without parents
    folder_children -- dict mapping channel folder ids to a list of
        ChannelInfo/PlaylistInfo objects for their children
    expanded_folders -- set containing ids of the folders that should
        be initially expanded.
    """

    def __init__(self, type):
        self.type = type
        self.toplevels = []
        self.folder_children = {}
        self.expanded_folders = set()

    def append(self, info):
        self.toplevels.append(info)
        if info.is_folder:
            self.folder_children[info.id] = []

    def append_child(self, parent_id, info):
        self.folder_children[parent_id].append(info)

    def expand_folder(self, folder_id):
        self.expanded_folders.add(folder_id)

class TabsChanged(FrontendMessage):
    """Informs the frontend that the channel list or playlist list has been 
    changed.

    Attributes:
    type -- 'feed', playlist' or 'guide'
    added -- ChannelInfo/PlaylistInfo object for each added tab.  The list 
        will be in the same order that the tabs were added.
    changed -- list of ChannelInfo/PlaylistInfos for each changed tab.
    removed -- list of ids for each tab that was removed
    section -- 'audio', 'video', or None (used for channels and
        channel folders)
    """
    def __init__(self, type, added, changed, removed, section=None):
        self.type = type
        self.added = added
        self.changed = changed
        self.removed = removed
        self.section = section

class ItemList(FrontendMessage):
    """Sends the frontend the initial list of items for a feed

    Attributes:
    type -- type of object being tracked (same as in TrackItems)
    id -- id of the object being tracked (same as in TrackItems)
    items -- list of ItemInfo objects
    """
    def __init__(self, type, id, item_infos):
        self.type = type
        self.id = id
        self.items = item_infos

class ItemsChanged(FrontendMessage):
    """Informs the frontend that the items in a feed have changed.

    Attributes:
    type -- type of object being tracked (same as in TrackItems)
    id -- id of the object being tracked (same as in TrackItems)
    added -- list containing an ItemInfo object for each added item.  The
        order will be the order they were added.
    changed -- set containing an ItemInfo for each changed item.
    removed -- set containing ids for each item that was removed
    """

    def __init__(self, type, id, added, changed, removed):
        self.type = type
        self.id = id
        self.added = added
        self.changed = changed
        self.removed = removed

class WatchedFolderList(FrontendMessage):
    """Sends the frontend the initial list of watched folders

    Attributes:
        watched_folders -- List of watched folders
    """

    def __init__(self, watched_folders):
        self.watched_folders = watched_folders

class WatchedFoldersChanged(FrontendMessage):
    """Informs the frontend that the watched folder list has changed.

    Attributes:
    added -- WatchedFolderInfo object for each added watched folder.  The list
        will be in the same order that they were added
    changed -- list of WatchedFolderInfo for each changed watched folder.
    removed -- list of ids for each watched folder that was removed.
    """

    def __init__(self, added, changed, removed):
        self.added = added
        self.changed = changed
        self.removed = removed

class CurrentSearchInfo(FrontendMessage):
    """Informs the frontend of the current search settings """
    def __init__(self, engine, text):
        self.engine = engine
        self.text = text

class DownloadCountChanged(FrontendMessage):
    """Informs the frontend that number of downloads has changed """

    def __init__(self, count):
        self.count = count

class PausedCountChanged(FrontendMessage):
    """Informs the frontend that number of paused downloading items has changed """
    def __init__(self, count):
        self.count = count

class NewCountChanged(FrontendMessage):
    """Informs the frontend that number of new videos has changed """

    def __init__(self, count):
        self.count = count

class UnwatchedCountChanged(FrontendMessage):
    """Informs the frontend that number of unwatched items has changed """
    def __init__(self, count):
        self.count = count

class MessageToUser(FrontendMessage):
    """Lets the backend send messages directly to the user."""
    def __init__(self, title, desc):
        self.title = title
        self.desc = desc

class PlayMovie(FrontendMessage):
    """Starts playing a specific movie."""
    def __init__(self, item_infos):
        self.item_infos = item_infos

class NotifyUser(FrontendMessage):
    """
    Sends a notification to the user.

    Can optionally give a notification type, so we can filter based on
    whether the user has selected that they are interested in
    receiving notifications of this type.
    """
    def __init__(self, title, body, notify_type=None):
        self.title = title
        self.body = body
        self.notify_type = notify_type
    
class SearchComplete(FrontendMessage):
    """Notifies the backend that the search was complete."""

    def __init__(self, engine, query, result_count):
        self.engine = engine
        self.query = query
        self.result_count = result_count

class CurrentFrontendState(FrontendMessage):
    """Returns the latest data saved with SaveFrontendState."""
    def __init__(self, list_view_displays, sort_states):
        self.list_view_displays = list_view_displays
        self.sort_states = sort_states

class OpenInExternalBrowser(FrontendMessage):
    """Opens the specified url in an external browser."""
    def __init__(self, url):
        self.url = url

class MigrationProgress(FrontendMessage):
    """Inform the frontend of progress while we migrate files."""
    def __init__(self, iteration, total_files, finished):
        self.iteration = iteration
        self.total_files = total_files
        self.finished = finished
