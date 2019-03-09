import os
import json
import subprocess
import math

import av

from .. import exceptions


def probe(vid_file_path):
    if type(vid_file_path) != str:
        raise Exception('Gvie ffprobe a full file path of the video')

    command = [
        "ffprobe",
        "-loglevel",
        "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        vid_file_path
    ]

    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = pipe.communicate()
    return json.loads(out)


def resize_video(input, output, width, height, debug=False):
    command = [
        "ffmpeg",
        "-i", input,
        "-vf", "scale=%d:%d" % (width, height),
        "-c:v", "libx264",
        "-profile:v", "main",
       "-crf", "20",
        output,
        "-y",
    ]
    if debug:
        print(' '.join(command))
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = pipe.communicate()
    if 'Error' in out:
        raise RuntimeError(out)


def get_video_info(vid_file_path):
    duration = None
    width, height = (None, None)

    _json = probe(vid_file_path)

    if 'format' in _json:
        if 'duration' in _json['format']:
            duration = float(_json['format']['duration'])

    if 'streams' in _json:
        # commonly stream 0 is the video
        for s in _json['streams']:
            if 'duration' in s:
                duration = float(s['duration'])
            if 'width' in s:
                width = s['width']
            if 'height' in s:
                height = s['height']

    if duration is None:
        raise Exception('I found no duration')
    if width is None:
        raise Exception('I found no width')
    if height is None:
        raise Exception('I found no height')
    return duration, (width, height)


def prepare_video(vid_file_path, debug=False):
    min_ratio = 0.8
    max_ratio = 1.6
    duration, (width, height) = get_video_info(vid_file_path)
    if duration < 3:
        raise exceptions.VideoTooShort('Video too short %s' % duration)
    ratio = float(width) / height
    result_path_list = list(os.path.split(vid_file_path))
    result_path_list[-1] = '*' + result_path_list[-1]
    result_path = os.path.join(*result_path_list)
    if ratio < min_ratio:
        diff_width = int(height * min_ratio - width) + 1
        if diff_width % 2 != 0:
            diff_width += 1
        new_width = diff_width + width
        resize_video(vid_file_path, result_path, new_width, height, debug=debug)
    elif ratio >= max_ratio:
        diff_height = int(width - height * max_ratio) + 1
        if diff_height % 2 != 0:
            diff_height += 1
        new_height = diff_height + height
        resize_video(vid_file_path, result_path, width, new_height, debug=debug)
    else:
        result_path = vid_file_path
    # if duration >= 60:
    #     another_result_path_list = list(os.path.split(result_path))
    #     another_result_path_list[-1] = '*' + result_path_list[-1]
    #     another_result_path_list = os.path.join(*another_result_path_list)
    #     cut_last(result_path, another_result_path_list, start_sec=int(math.ceil(duration - 60)), debug=True)
    #     result_path = another_result_path_list
    return result_path


def split_by_parts(value, count):
    length = len(value)
    step = int(math.ceil(length * 1.0 / count))
    start_index = 0
    end_index = 0
    exit_loop = False
    while not exit_loop:
        end_index += step
        if end_index >= length:
            exit_loop = True
            end_index = length
        yield start_index, end_index, value[start_index:end_index]
        start_index = end_index


def video_preview(video_path):
    preview_name = f"{os.path.basename(video_path).split('.')[0]}_preview.jpeg"
    preview_path = os.path.join('/tmp/', preview_name)
    container = av.open(video_path)
    frame = next(container.decode(video=0))
    frame.to_image().save(preview_path)
    return preview_path
