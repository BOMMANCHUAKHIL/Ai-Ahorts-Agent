class MusicSelector:
    def __init__(self, tracks):
        self.tracks = tracks
        self.index = 0

    def next(self):
        track = self.tracks[self.index % len(self.tracks)]
        self.index += 1
        return track