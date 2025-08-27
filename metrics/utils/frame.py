import pandas


def concat_frames(frames: list[pandas.DataFrame], columns: list[str]) -> pandas.DataFrame:
    frames = [i for i in frames if len(i) > 0]  # remove empty frames
    if len(frames) > 0:
        return pandas.concat(frames)
    else:
        return pandas.DataFrame(columns=columns)
