""" mqtt-mediaplayer """
import logging
import homeassistant.loader as loader
import hashlib
import voluptuous as vol
import base64
from homeassistant.exceptions import TemplateError, NoEntitySpecifiedError
from homeassistant.helpers.script import Script
from homeassistant.helpers.event import TrackTemplate, async_track_template_result, async_track_state_change
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import (
    CONF_NAME,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_IDLE,
)
import homeassistant.helpers.config_validation as cv

DEPENDENCIES = ["mqtt"]

_LOGGER = logging.getLogger(__name__)

# TOPICS
TOPICS = "topic"
SONGTITLE_T = "song_title"
SONGARTIST_T = "song_artist"
SONGALBUM_T = "song_album"
VOL_T = "volume"
ALBUMART_T = "album_art"
ALBUMARTURL_T = "album_art_url"
PLAYERSTATUS_T = "player_status"
SOURCE_T = "source"
SOURCELIST_T = "sourcelist"
MUTE_T = "mute"
POWER_T = "power"


# END of TOPICS

NEXT_ACTION = "next"
PREVIOUS_ACTION = "previous"
PLAY_ACTION = "play"
PAUSE_ACTION = "pause"
STOP_ACTION = "stop"
POWER_ON_ACTION = "power_on"
POWER_OFF_ACTION = "power_off"
VOL_DOWN_ACTION = "vol_down"
VOL_UP_ACTION = "vol_up"
VOL_MUTE_ACTION = "vol_mute"
VOL_UNMUTE_ACTION = "vol_unmute"
VOLUME_ACTION = "volume"
SELECT_SOURCE_ACTION = "select_source"
PLAYERSTATUS_KEYWORD = "status_keyword"

SUPPORT_MQTTMEDIAPLAYER = (
    SUPPORT_PLAY
    | SUPPORT_PAUSE
    | SUPPORT_STOP
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_STEP
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_SELECT_SOURCE
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(TOPICS):
            vol.All({
                vol.Optional(SONGTITLE_T): cv.template,
                vol.Optional(SONGARTIST_T): cv.template,
                vol.Optional(SONGALBUM_T): cv.template,
                vol.Optional(VOL_T): cv.template,
                vol.Optional(PLAYERSTATUS_T): cv.template,
                vol.Optional(ALBUMARTURL_T): cv.string,
                vol.Optional(ALBUMART_T): cv.string,
                vol.Optional(POWER_T): cv.string,
                vol.Optional(MUTE_T): cv.string,
                vol.Optional(SOURCE_T): cv.string,
                vol.Optional(SOURCELIST_T): cv.string,
            }),
        vol.Optional(NEXT_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(PREVIOUS_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(PLAY_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(PAUSE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(STOP_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(VOLUME_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(VOL_DOWN_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(VOL_UP_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(VOL_MUTE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(VOL_UNMUTE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(POWER_ON_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(POWER_OFF_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(SELECT_SOURCE_ACTION): cv.SCRIPT_SCHEMA,
        vol.Optional(PLAYERSTATUS_KEYWORD): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the MQTT Media Player platform."""
    mqtt = hass.components.mqtt

    topics = config.get(TOPICS)
    entity_name = config.get(CONF_NAME)
    next_action = config.get(NEXT_ACTION)
    previous_action = config.get(PREVIOUS_ACTION)
    play_action = config.get(PLAY_ACTION)
    pause_action = config.get(PAUSE_ACTION)
    stop_action = config.get(STOP_ACTION)
    vol_down_action = config.get(VOL_DOWN_ACTION)
    vol_up_action = config.get(VOL_UP_ACTION)
    vol_mute_action = config.get(VOL_MUTE_ACTION)
    vol_unmute_action = config.get(VOL_UNMUTE_ACTION)
    volume_action = config.get(VOLUME_ACTION)
    power_on_action = config.get(POWER_ON_ACTION)
    power_off_action = config.get(POWER_OFF_ACTION)
    select_source_action = config.get(SELECT_SOURCE_ACTION)
    player_status_keyword = config.get(PLAYERSTATUS_KEYWORD)

    add_entities([MQTTMediaPlayer(
        entity_name, next_action, previous_action, play_action, pause_action, stop_action,
        vol_down_action, vol_up_action, vol_mute_action, vol_unmute_action, volume_action, power_on_action, power_off_action, select_source_action, player_status_keyword,
        topics, mqtt, hass
    )], )


class MQTTMediaPlayer(MediaPlayerEntity):

    """MQTTMediaPlayer"""

    def __init__(self, name, next_action, previous_action, play_action, pause_action, stop_action,
                 vol_down_action, vol_up_action, vol_mute_action, vol_unmute_action, volume_action, power_on_action, power_off_action, select_source_action, player_status_keyword, 
                 topics, mqtt, hass):
        """Initialize"""
        self.hass = hass
        self._domain = __name__.split(".")[-2]
        self._name = name
        self._volume = 0.0
        self._track_name = ""
        self._track_artist = ""
        self._track_album_name = ""
        self._mqtt_player_state = None
        self._state = None
        self._album_art = None
        self._source = None
        self._source_list = []
        self._mute = False
        self._power = "standby"
        self._next_script = None
        self._previous_script = None
        self._play_script = None
        self._pause_script = None
        self._stop_script = None
        self._vol_down_script = None
        self._vol_up_script = None
        self._vol_mute_script = None
        self._vol_unmute_script = None
        self._vol_script = None
        self._power_on_script = None
        self._power_off_script = None
        self._select_source_script = None

        if(next_action):
            self._next_script = Script(
                hass, next_action, self._name, self._domain)
        if(previous_action):
            self._previous_script = Script(
                hass, previous_action, self._name, self._domain)
        if(play_action):
            self._play_script = Script(
                hass, play_action, self._name, self._domain)
        if(pause_action):
            self._pause_script = Script(
                hass, pause_action, self._name, self._domain)
        if(stop_action):
            self._stop_script = Script(
                hass, stop_action, self._name, self._domain)
        if(vol_down_action):
            self._vol_down_script = Script(
                hass, vol_down_action, self._name, self._domain)
        if(vol_up_action):
            self._vol_up_script = Script(
                hass, vol_up_action, self._name, self._domain)
        if(vol_mute_action):
            self._vol_mute_script = Script(
                hass, vol_mute_action, self._name, self._domain)
        if(vol_unmute_action):
            self._vol_unmute_script = Script(
                hass, vol_unmute_action, self._name, self._domain)
        if(volume_action):
            self._vol_script = Script(
                hass, volume_action, self._name, self._domain)
        if(power_on_action):
            self._power_on_script = Script(
                hass, power_on_action, self._name, self._domain)
        if(power_off_action):
            self._power_off_script = Script(
                hass, power_off_action, self._name, self._domain)
        if(select_source_action):
            self._select_source_script = Script(
                hass, select_source_action, self._name, self._domain)

        self._player_status_keyword = player_status_keyword

        if topics is not None:
            for key, value in topics.items():

                if key == SONGTITLE_T:
                    result = async_track_template_result(
                        self.hass, [TrackTemplate(value, None)], self.tracktitle_listener)
                    self.async_on_remove(result.async_remove)

                if key == SONGARTIST_T:
                    result = async_track_template_result(
                        self.hass, [TrackTemplate(value, None)], self.artist_listener)
                    self.async_on_remove(result.async_remove)

                if key == SONGALBUM_T:
                    result = async_track_template_result(
                        self.hass, [TrackTemplate(value, None)], self.album_listener)
                    self.async_on_remove(result.async_remove)

                if key == VOL_T:
                    result = async_track_template_result(
                        self.hass, [TrackTemplate(value, None)], self.volume_listener)
                    self.async_on_remove(result.async_remove)

                if key == ALBUMART_T:
                    mqtt.subscribe(value, self.albumart_listener)

                if key == ALBUMARTURL_T:
                    mqtt.subscribe(value, self.albumarturl_listener)

                if key == MUTE_T:
                    mqtt.subscribe(value, self.mute_listener)

                if key == POWER_T:
                    mqtt.subscribe(value, self.power_listener)
                
                if key == SOURCE_T:
                    mqtt.subscribe(value, self.source_listener)
                
                if key == SOURCELIST_T:
                    mqtt.subscribe(value, self.sourcelist_listener)

                if key == PLAYERSTATUS_T:
                    result = async_track_template_result(
                        self.hass, [TrackTemplate(value, None)], self.state_listener)
                    self.async_on_remove(result.async_remove)

    async def tracktitle_listener(self, event, updates):
        """Listen for the Track Title change"""
        result = updates.pop().result
        self._track_name = result
        if MQTTMediaPlayer:
            self.schedule_update_ha_state(True)

    async def artist_listener(self, event, updates):
        """Listen for the Artis Name change"""
        result = updates.pop().result
        self._track_artist = result

    async def album_listener(self, event, updates):
        """Listen for the Album Name change"""
        result = updates.pop().result
        self._track_album_name = result

    async def volume_listener(self, event, updates):
        """Listen for Player Volume changes"""
        result = updates.pop().result
        _LOGGER.debug("Volume Listener: " + str(result))
        if isinstance(result, int):
            self._volume = int(result) / 100.0
            if MQTTMediaPlayer:
                self.schedule_update_ha_state(True)

    async def albumart_listener(self, msg):
        """Listen for the Album Art change"""
        self._album_art = base64.b64decode(msg.payload.replace("\n", ""))

    async def mute_listener(self, msg):
        """Listen for the Album Art change"""
        self._mute = msg.payload
        if MQTTMediaPlayer:
            self.schedule_update_ha_state(True)

    async def power_listener(self, msg):
        """Listen for the Album Art change"""
        self._power = msg.payload
        if MQTTMediaPlayer:
            self.schedule_update_ha_state(True)

    async def source_listener(self, msg):
        """Listen for the Album Art change"""
        self._source = msg.payload

    async def sourcelist_listener(self, msg):
        """Listen for the Album Art change"""
        self._source_list = msg.payload

    async def state_listener(self, event, updates):
        """Listen for Player State changes"""
        result = updates.pop().result
        self._mqtt_player_state = str(result)
        if MQTTMediaPlayer:
            self.schedule_update_ha_state(True)

    def update(self):
        """ Update the States"""
        if self._power != "on":
            self._state = STATE_OFF
        elif self._player_status_keyword:
            if self._mqtt_player_state == self._player_status_keyword:
                self._state = STATE_PLAYING
            else:
                self._state = STATE_PAUSED

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume 

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._mute == True or self._mute == "true"

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_title(self):
        """Title of current playing media."""
        return self._track_name

    @property
    def media_artist(self):
        """Artist of current playing media, music track only."""
        return self._track_artist

    @property
    def media_album_name(self):
        """Album name of current playing media, music track only."""
        return self._track_album_name

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_MQTTMEDIAPLAYER

    @property
    def media_image_hash(self):
        """Hash value for media image."""
        if self._album_art:
            return hashlib.md5(self._album_art).hexdigest()[:5]
        return None

    @property
    def source(self):
        """Name of the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return ["test","spotify"]
        return self._source_list

    @property
    def shuffle(self):
        """Boolean if shuffle is enabled."""
        return None

    @property
    def repeat(self):
        """Return current repeat mode."""
        return None

    async def async_get_media_image(self):
        """Fetch media image of current playing image."""
        if self._album_art:
            return (self._album_art, "image/jpeg")
        return None, None

    async def async_turn_on(self):
        """Turn the media player on."""
        if self._power_on_script:
            await self._power_on_script.async_run(context=self._context)

    async def async_turn_off(self):
        """Turn the media player off."""
        if self._power_off_script:
            await self._power_off_script.async_run(context=self._context)

    async def async_volume_up(self):
        """Volume up the media player."""
        if self._vol_up_script:
            await self._vol_up_script.async_run(context=self._context)
        else:
            newvolume = min(self._volume + 0.05, 1)
            self._volume = newvolume
            await self.async_set_volume_level(newvolume)

    async def async_volume_down(self):
        """Volume down media player."""
        if self._vol_down_script:
            await self._vol_down_script.async_run(context=self._context)
        else:
            newvolume = max(self._volume - 0.05, 0)
            self._volume = newvolume
            await self.async_set_volume_level(newvolume )
    
    async def async_set_volume_level(self, volume):
        """Set volume level."""
        if(self._vol_down_script or self._vol_up_script):
            return
        if(self._vol_script):
            await self._vol_script.async_run({"volume": volume * 100}, context=self._context)
            self._volume = volume
    
    async def async_mute_volume(self, mute):
        if mute:
            if self._vol_mute_script:
                _LOGGER.error("test 1")
                await self._vol_mute_script.async_run(context=self._context)
        else:
            if self._vol_unmute_script:
                _LOGGER.error("test 2 ")
                await self._vol_unmute_script.async_run(context=self._context)

    async def async_media_play_pause(self):
        """Simulate play pause media player."""
        if self._state == STATE_PLAYING:
            await self.async_media_pause()
        else:
            await self.async_media_play()

    async def async_media_play(self):
        """Send play command."""
        if self._play_script:
            await self._play_script.async_run(context=self._context)
            self._state = STATE_PLAYING

    async def async_media_pause(self):
        """Send media pause command to media player."""
        if self._pause_script:
            await self._pause_script.async_run(context=self._context)
            self._state = STATE_PAUSED

    async def async_media_stop(self):
        """Send media stop command to media player."""
        if self._stop_script:
            await self._stop_script.async_run(context=self._context)
            self._state = STATE_IDLE

    async def async_media_next_track(self):
        """Send next track command."""
        if self._next_script:
            await self._next_script.async_run(context=self._context)

    async def async_media_previous_track(self):
        """Send the previous track command."""
        if self._previous_script:
            await self._previous_script.async_run(context=self._context)

    async def async_select_source(self, source):
        """Select input source."""
        if self._select_source_script:
            await self._select_source_script.async_run({"source": source}, context=self._context)
