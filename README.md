# hass-mqtt-mediaplayer

Allows you to use MQTT topics to fill out the information needed for the Home Assistant Media Player Entity

## Supported Services

[Media Player Entity](https://www.home-assistant.io/integrations/media_player/)

* volume_up
* volume_down
* volume_set
* media_play_pause
* media_play
* media_pause
* media_next_track
* media_previous_track

## Options

| Variables      | Type                                                                      | Default  | Description                                                                       | Expected Payload            | Example                                                                 |
|----------------|---------------------------------------------------------------------------|----------|-----------------------------------------------------------------------------------|-----------------------------|-------------------------------------------------------------------------|
| name           | string                                                                    | required | Name for the entity                                                               | string                      | ```"Musicbee"```                                                        |
| song_title     | [template](https://www.home-assistant.io/integrations/template/)                                                                    | optional | Value for the song title                                             | string                      | * see configuration.yaml ex.                                              |
| song_artist    | [template](https://www.home-assistant.io/integrations/template/)                                                                    | optional | Value for the song artist                                            | string                      | * see configuration.yaml ex.                                                 |
| song_album     | [template](https://www.home-assistant.io/integrations/template/)                                                                    | optional | Value for the song album                                        | string                      | * see configuration.yaml ex.                                                  |
| song_volume    | [template](https://www.home-assistant.io/integrations/template/)                                                                    | optional | Value for the player volume                                          | int (0 to 100)       | * see configuration.yaml ex.                                                 |
| album_art      | string                                                                    | optional | Topic to listen to for the song album art (Must be a base64 encoded string)       | string (base64 encoded url) | ```"musicbee/albumart"```                                               |
| player_status  | [template](https://www.home-assistant.io/integrations/template/)                                                                    | optional | Value for the player status                         | string                      | * see configuration.yaml ex.                                          |
| vol_down*          | [service call](https://www.home-assistant.io/docs/scripts/service-calls/) | optional | MQTT service to call for the media_player.volume_down command                           | N/A                         | * see configuration.yaml ex.                                                |
| vol_up*          | [service call](https://www.home-assistant.io/docs/scripts/service-calls/) | optional | MQTT service to call for the media_player.volume_up command                           | N/A                         | * see configuration.yaml ex.                                                |
| volume      | [service call](https://www.home-assistant.io/docs/scripts/service-calls/)                                                                    | optional | MQTT service to call for the media_player.volume_set command                                    | string                      | * see configuration.yaml                                                |
| status_keyword* | string                                                                    | optional | Keyword used to indicate your MQTT enabled player is currently playing a song     | string                      | ```"true"```                                                            |
| next           | [service call](https://www.home-assistant.io/docs/scripts/service-calls/) | optional | MQTT service to call when the "next" button is pressed                            | N/A                         | * see configuration.yaml ex.                                                |
| previous       | [service call](https://www.home-assistant.io/docs/scripts/service-calls/) | optional | MQTT service to call when the "previous" button is pressed                        | N/A                         | * see configuration.yaml ex.                                                |
| play           | [service call](https://www.home-assistant.io/docs/scripts/service-calls/) | optional | MQTT service to call when the "play" button is pressed                            | N/A                         | * see configuration.yaml ex.                                                |
| pause          | [service call](https://www.home-assistant.io/docs/scripts/service-calls/) | optional | MQTT service to call when the "pause" button is pressed                           | N/A                         | * see configuration.yaml ex.                                                |

*NOTES:

 * volume: put your custom payload here and replace where your value would be with ``"{{volume}}"`` (see config ex.)
 * status_keyword: This is the keyword your player publishes when it is PLAYING. You only need to mention the keyword for playing. For example, my player indicates it is playing by publishing ```playing = true``` to my broker. Therefore I enter ```"true"``` in my configuration.yaml
 * vol_up/vol_down: Setting this disables the volume_set service. Use vol_up/vol_down if your media player doesn't publish a volume level (i.e if your media player only responds to simple "volumeup"/"volumedown" commands. **If you use the "volume" topic you DONT need to use vol_up/vol_down. Same for the reverse**
 
 
 
## Example configuration.yaml

```yaml
media_player:  
  - platform: mqtt-mediaplayer
    name: Rotel
    unique_id: some-unique-d
    topic:
      sourcelist: "{{ states('sensor.rotel_config_source_list') }}"
      source: "{{ states('sensor.rotel_state_source') }}"
      power: "{{ states('sensor.rotel_state_power') }}"
    power_on:
      service: mqtt.publish
      data:
        topic: "rotel/command"
        payload: '{"command": "power_on"}'
    power_off:
      service: mqtt.publish
      data:
        topic: "rotel/command"
        payload: '{"command":"power_off"}'
    vol_up:
      service: mqtt.publish
      data:
        topic: "rotel/command"
        payload: '{"command":"volume_up"}'
    vol_down:
      service: mqtt.publish
      data:
        topic: "rotel/command"
        payload: '{"command":"volume_down"}'
    vol_mute:
      service: mqtt.publish
      data:
        topic: "rotel/command"
        payload: '{"command":"mute_toggle"}'
    vol_unmute:
      service: mqtt.publish
      data:
        topic: "rotel/command"
        payload: '{"command":"mute_toggle"}'
    select_source:
      service: mqtt.publish
      data:
        topic: "rotel/source/set"
        payload_template: '{"source": "{{ source }}"}'

```

## Example MQTT Broker

This is what my player outputs and what I see when I use MQTT Explorer

```
musicbee
	playing = true
	songtitle = Repeat After Me (Interlude)
	artist = The Weeknd
	volume = 86
	album = After Hours
	command = {"command": "next"}
	albumart = /9j/4AAQSkZJRgABAQEASABI ...
```
