import json
import pydub
import os
import numpy as np
from tinytag import TinyTag


def read_mp3_audio(audio_file, normalized=False):
    """MP3 to numpy array"""
    a = pydub.AudioSegment.from_mp3(audio_file)
    a = pydub.AudioSegment.silent(3000) + a
    output_dir = os.path.basename(audio_file)[:-4]
    if not os.path.exists(f'{output_dir}'):
        os.makedirs(f'{output_dir}')
    a.export(f'{output_dir}/song.egg', format='ogg')
    y = np.array(a.get_array_of_samples())

    if a.channels == 2:
        y = y.reshape((-1, 2))
    if normalized:
        return a.frame_rate, np.float32(y) / 2**15
    else:
        return a.frame_rate, y


def create_info_data(name, artist, bpm, out_folder):
    with open('Info.dat', 'r') as info:
        json_dict = json.load(info)

    json_dict['_songName'] = name
    json_dict['_songAuthorName'] = artist
    json_dict['_beatsPerMinute'] = bpm
    json_writable = json.dumps(json_dict)

    with open(f'{out_folder}/Info.dat', 'w') as new_info:
        new_info.write(json_writable)


def write_bs_map_string(path, map_string: str):
    map_string = '{"_version":"2.2.0",' + map_string + '"_obstacles":[],"_waypoints":[]}'
    output_dir = os.path.basename(path)[:-4]
    with open(f'{output_dir}/NormalStandard.dat', 'w') as f:
        f.write(map_string)


def read_song_metadata(song_path):
    audio = TinyTag.get(song_path)
    try:
        title = audio.title
        if title == '':
            title = os.path.basename(song_path)
    except:
        title = os.path.basename(song_path)
    try:
        artist = audio.artist
        if artist == '':
            artist = 'unknown'
    except:
        artist = 'unknown'
    return title, artist
