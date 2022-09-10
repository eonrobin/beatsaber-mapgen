import numpy as np
import aubio
import matplotlib.pyplot as plot
import file_operations


def freq_transform(signal, n_fft, frameshift):
    han_win = np.hanning(n_fft)
    signal_frame = signal[frameshift:frameshift + n_fft]
    signal_frame = signal_frame[::-1]
    signal_frame_win = signal_frame * han_win
    frame_frequency = np.fft.fft(signal_frame_win)[0:int(n_fft / 2)]
    frame_frequency[frame_frequency < 0] = frame_frequency[frame_frequency < 0] * -1
    return frame_frequency


def calc_bpm(signal, path):
    s = aubio.source(path, 44100, 256)
    samplerate = s.samplerate
    o = aubio.tempo("specdiff", 512, 256, samplerate)
    # List of beats, in samples
    beats = []
    # Total number of frames read
    total_frames = 0

    while True:
        samples, read = s()
        is_beat = o(samples)
        if is_beat:
            this_beat = o.get_last_s()
            beats.append(this_beat)
        total_frames += read
        if read < 256:
            break

    def beats_to_bpm(beats, path):
        # if enough beats are found, convert to periods then to bpm
        if len(beats) > 1:
            if len(beats) < 4:
                print("few beats found in {:s}".format(path))
            bpms = 60. / np.diff(beats)
            return np.median(bpms)
        else:
            print("not enough beats found in {:s}".format(path))
            return 0

    return beats_to_bpm(beats, path)


def analyse_song(audio_path, fade_time=3, n_fft=512, beat_factor=2000):
    num_sectors = 4
    frameshift = int(n_fft / 2)
    sample_rate, audio_array = file_operations.read_mp3_audio(audio_path)
    intensity_maximum = max(audio_array[:, 0])
    intensity_threshold = intensity_maximum / 2
    fade_samples = fade_time * sample_rate
    audio_length = len(audio_array[fade_samples:-fade_samples, 0])

    result_array = np.zeros((int(n_fft / 2), int(audio_length) + 1))
    beat_array = np.zeros(int(audio_length))
    weight_array = np.zeros(int(audio_length))

    for side_idx in range(0, 1):
        analyse_samples = 0
        cycle = 0

        while analyse_samples + frameshift <= audio_length - frameshift:
            result_array[:, cycle] = freq_transform(audio_array[fade_samples:-fade_samples, side_idx], n_fft,
                                                    analyse_samples)
            if cycle != 0:
                freq_stepper = 0
                max_frame_intensity = 0

                for freq in result_array[:, cycle]:
                    lock = False
                    if freq >= intensity_threshold:
                        if freq / result_array[freq_stepper, cycle - 1] >= beat_factor:
                            if freq >= max_frame_intensity:
                                weight_array[analyse_samples + frameshift] += freq - max_frame_intensity
                                max_frame_intensity = freq
                                for sector in range(1, num_sectors+1):
                                    if not lock:
                                        if freq_stepper <= (n_fft / 2) / num_sectors * sector:
                                            if beat_array[analyse_samples + frameshift] == sector:
                                                weight_array[analyse_samples + frameshift] *= 2
                                            else:
                                                beat_array[analyse_samples + frameshift] = sector
                                                lock = True
                    freq_stepper += 1
            analyse_samples += frameshift
            cycle += 1
    npm = len(beat_array[beat_array > 0]) / (len(audio_array[:, 0]) / sample_rate / 60)

    print(f'Notes - 1:{len(beat_array[beat_array == 1])}; 2:{len(beat_array[beat_array == 2])}; '
          f'3:{len(beat_array[beat_array == 3])}; 4:{len(beat_array[beat_array == 4])};')

    return beat_array, weight_array, sample_rate, calc_bpm(audio_array[:, 0], audio_path), npm


def add_note_entry(entry_string, time_entry, index_entry, layer_entry, type_entry, cut_entry):
    entry_string = f'{entry_string}{{"_time":{time_entry},' \
                  f'"_lineIndex":{index_entry},' \
                  f'"_lineLayer":{layer_entry},' \
                  f'"_type":{type_entry},' \
                  f'"_cutDirection":{cut_entry}}},'
    return entry_string


def set_notes(beat_data, weight_data, tempo_data, sample_rate, beats):
    from enum import Enum

    class NoteType(Enum):
        LEFT_SIDE_NOTE = 0
        RIGHT_SIDE_NOTE = 1
        BOMB = 2

    beat_data[0:int(3 * sample_rate - 1)] = 0
    bps = beats / 60
    file_string = '"_notes":['
    left_saber_is_up = 0
    right_saber_is_up = 0
    is_locked = False
    lock_counter = 0
    last_note_type = NoteType.RIGHT_SIDE_NOTE
    toggle = {0: 1, 1: 0}
    left_line_distribution = {1: 1, 2: 0, 3: 1, 4: 2}
    right_line_distribution = {1: 2, 2: 3, 3: 2, 4: 1}

    weight_threshold_for_double = max(weight_data)/2

    for t in range(int(3 * sample_rate - 1), len(beat_data) - 1):
        if tempo_data[t] == 1:
            lock_samples = sample_rate / 4
        else:
            lock_samples = sample_rate / 2

        if weight_data[t] >= weight_threshold_for_double:
            if lock_counter >= sample_rate * 0.2:
                note_time = round(t / sample_rate * bps, 3)
                # Left double note block
                note_layer = toggle[left_saber_is_up]
                note_cutdir = left_saber_is_up
                left_saber_is_up = toggle[left_saber_is_up]
                file_string = add_note_entry(file_string, note_time, 1, note_layer, 0, note_cutdir)
                # Right double note block
                note_layer = toggle[right_saber_is_up]
                note_cutdir = left_saber_is_up
                right_saber_is_up = toggle[right_saber_is_up]
                file_string = add_note_entry(file_string, note_time, 2, note_layer, 1, note_cutdir)
                is_locked = True

        if not is_locked:
            lock_counter = 0
            if beat_data[t] != 0:
                note_time = round(t / sample_rate * bps, 3)
                if last_note_type == NoteType.RIGHT_SIDE_NOTE:
                    last_note_type = NoteType.LEFT_SIDE_NOTE
                else:
                    last_note_type = NoteType.RIGHT_SIDE_NOTE
                note_type = last_note_type.value

                if last_note_type == NoteType.LEFT_SIDE_NOTE:
                    # Left single note block
                    note_line = left_line_distribution[beat_data[t]]
                    note_layer = toggle[left_saber_is_up]
                    note_cutdir = left_saber_is_up
                    left_saber_is_up = toggle[left_saber_is_up]
                else:
                    # Right single note block
                    note_line = right_line_distribution[beat_data[t]]
                    note_layer = toggle[right_saber_is_up]
                    note_cutdir = right_saber_is_up
                    right_saber_is_up = toggle[right_saber_is_up]
                file_string = add_note_entry(entry_string=file_string, time_entry=note_time, index_entry=note_line,
                                             layer_entry=note_layer, type_entry=note_type, cut_entry=note_cutdir)
                is_locked = True
        else:
            lock_counter += 1
            if lock_counter >= lock_samples:
                is_locked = False

    return file_string[:-1] + '],'


def add_event_entry(entry_string, time_entry, type_entry, value_entry):
    entry_string = f'{entry_string}{{"_time":{time_entry},' \
                  f'"_type":{type_entry},' \
                  f'"_value":{value_entry}}},'
    return entry_string


def set_events(beat_data, weight_data, tempo_data, sample_rate, beats):
    bps = beats / 60
    file_string = '"_events":['

    beat_data[0:int(3 * sample_rate - 1)] = 0
    bottom_light_is_on = False
    right_cross_is_on = False
    left_cross_is_on = False
    side_toggle = 0
    toggle = {0: 1, 1: 0}

    weight_threshold = max(weight_data) / 10

    for t in range(0, len(beat_data) - 1):
        # left side notes
        beat = beat_data[t]
        if beat >= 1:
            time_entry = round(t / sample_rate * bps, 3)
            if weight_data[t] >= weight_threshold:
                if weight_data[t] >= weight_threshold*7:
                    type_entry = 2 + side_toggle
                    if right_cross_is_on and side_toggle == 1:
                        value_entry = 0
                        right_cross_is_on = False
                    elif left_cross_is_on and side_toggle == 0:
                        value_entry = 0
                        left_cross_is_on = False
                    else:
                        if side_toggle == 1:
                            right_cross_is_on = True
                        else:
                            left_cross_is_on = True
                        value_entry = 1
                    side_toggle = toggle[side_toggle]

                    file_string = add_event_entry(file_string, time_entry, type_entry, value_entry)
                    if beat == 1:
                        type_entry = 1
                        value_entry = 3 + side_toggle
                        file_string = add_event_entry(file_string, time_entry, type_entry, value_entry)
                else:
                    type_entry = 0
                    value_entry = 3 + side_toggle
                    side_toggle = toggle[side_toggle]
                    file_string = add_event_entry(file_string, time_entry, type_entry, value_entry)
        if tempo_data[t] == 1 and not bottom_light_is_on:
            time_entry = round(t / sample_rate * bps, 3)
            type_entry = 4
            value_entry = 1
            bottom_light_is_on = True
            file_string = add_event_entry(file_string, time_entry, type_entry, value_entry)
        elif tempo_data[t] == 0 and bottom_light_is_on:
            time_entry = round(t / sample_rate * bps, 3)
            type_entry = 4
            value_entry = 0
            bottom_light_is_on = False
            file_string = add_event_entry(file_string, time_entry, type_entry, value_entry)
    return file_string[:-1] + '],'


def evaluate_tempo(notes, frame_size=400000):
    start = 0
    length = len(notes)
    tempo_array = np.zeros(int(length))
    tempo_array[notes > 0] = 1
    tempo_factor = 0.5
    while start + frame_size <= length:
        tempo_array[start:start+int(frame_size/4)] = sum(notes[start:start+frame_size])
        start += int(frame_size/4)
    tempo_max = max(tempo_array)
    tempo_array[tempo_array < tempo_max * tempo_factor] = 0
    tempo_array[tempo_array >= tempo_max * tempo_factor] = 1
    return tempo_array


def show_graph(y):
    plot.plot(y)
    #plot.plot(audio)
    plot.show()
