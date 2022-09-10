import wx
import os

# File imports
import file_operations
import map_notes

# The recommended way to use wx with mpl is with the WXAgg
# backend.
#
import matplotlib

matplotlib.use('WXAgg')


class MyFrame(wx.Frame):
    path = ""
    """ We simply derive a new class of Frame. """

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(1000, 700))

        self.panel = wx.Panel(self)
        self.font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        self.font.SetPointSize(12)
        self.panel.SetBackgroundColour('#E5E7E6')
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.rw_hbox0 = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_song = wx.StaticText(self.panel, label='Choose a song:')
        self.lbl_song.SetFont(self.font)
        self.rw_hbox0.Add(self.lbl_song, proportion=0, flag=wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, border=20)
        self.tc_song = wx.TextCtrl(self.panel)
        self.rw_hbox0.Add(self.tc_song, proportion=2, flag=wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, border=20)
        self.btn_select = wx.Button(self.panel, label='Select', size=(70, 30))
        self.rw_hbox0.Add(self.btn_select, proportion=1, flag=wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, border=20)
        self.vbox.Add(self.rw_hbox0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=20)

        self.rw_hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_gen = wx.Button(self.panel, label='Generate Map', size=(70, 30))
        self.rw_hbox1.Add(self.btn_gen, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=20)
        self.vbox.Add(self.rw_hbox1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=20)

        self.rw_hbox_last = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_close = wx.Button(self.panel, label='Close', size=(70, 30))
        self.rw_hbox_last.Add(self.btn_close, proportion=1)
        self.vbox.Add(self.rw_hbox_last, flag=wx.ALIGN_RIGHT | wx.RIGHT | wx.TOP, border=10)

        self.Bind(wx.EVT_BUTTON, self.select_file, self.btn_select)
        self.Bind(wx.EVT_BUTTON, self.start_map_gen, self.btn_gen)
        self.Bind(wx.EVT_BUTTON, self.OnQuit, self.btn_close)

        self.panel.SetSizer(self.vbox)
        self.Show(True)

    def OnQuit(self, e):
        self.Close()

    def select_file(self, event):
        open_file_dialog = wx.FileDialog(self, "Open", "", "", "MP3 Files (*.mp3)|*.mp3",
                                         wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        open_file_dialog.ShowModal()
        print(open_file_dialog.GetPath())
        self.path = open_file_dialog.GetPath()
        self.tc_song.write(self.path)
        open_file_dialog.Destroy()
        return

    def start_map_gen(self, event):
        generate_map(self.path)


def generate_map(path):
    if path.endswith('.mp3'):
        max_npm = 250
        npm = max_npm + 1
        beat_thresh = 2000
        fft_size = 512
        fade_in = 3
        while npm > max_npm:
            beat_thresh += 1000
            beat_array, weights, sample_rate, bpm, npm = map_notes.analyse_song(path, fade_time=fade_in, n_fft=fft_size,
                                                                                beat_factor=beat_thresh)
            print(f'NPM= {npm}')
        print(f'BPM= {bpm}')
        tempo_array = map_notes.evaluate_tempo(notes=beat_array)
        file_operations.write_bs_map_string(path, map_notes.set_notes(beat_data=beat_array, weight_data=weights,
                                                                      tempo_data=tempo_array, sample_rate=sample_rate,
                                                                      beats=bpm) +
                                            map_notes.set_events(beat_data=beat_array, weight_data=weights,
                                                                 tempo_data=tempo_array, sample_rate=sample_rate,
                                                                 beats=bpm))

        output_dir = os.path.basename(path)[:-4]
        song_title, song_artist = file_operations.read_song_metadata(path)
        file_operations.create_info_data(song_title, song_artist, round(bpm, 0), output_dir)
        print('Aaaaaand done')


if __name__ == '__main__':
    app = wx.App(False)
    frame = MyFrame(None, 'BS Map Gen')
    app.MainLoop()
