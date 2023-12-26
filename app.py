import os
import ffmpeg
import uuid
import streamlit as st
import shutil
import logging

logging.basicConfig(level=logging.INFO)  # Set the logging level

def log_info(message):
    logging.info(message)

def log_error(error_message):
    logging.error(error_message)

# Function to extract audio using ffmpeg
def convert_audio(input_file):
    audio_file = f"{input_file}.wav"
    ffmpeg.input(input_file).output(audio_file, ar=48000, ac=1).run()
    return audio_file

# Function to split audio into segments
def split_audio(audio_file):
    segment_pattern = os.path.splitext(audio_file)[0] + ".segmented_%03d.wav"
    ffmpeg.input(audio_file).output(segment_pattern, f="segment", segment_time=300).run()
    return segment_pattern

# Function to filter each audio segment
def filter_audio(segments):
    filtered_dir = "temp-out"
    os.makedirs(filtered_dir, exist_ok=True)
    os.system(f"deepFilter -a 20 -o {filtered_dir} {segments.replace('%03d.wav', '')}*.wav")
    os.system(f"rm {segments.replace('%03d.wav', '')}*.wav")
    return filtered_dir

# Function to combine filtered segments using sox
def combine_segments(filtered_dir, output_file):
    os.system(f"sox {filtered_dir}/*.wav {output_file}")
    return output_file

# Function to check if input file is video
def is_video(input_file):
    result = os.popen(f"ffprobe -v error -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 {input_file}").read()
    return "video" in result.lower()

# Function to get format info for audio files
def get_format_info(input_file):
    result = os.popen(f"ffprobe -v error -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 {input_file}").read()
    return result


# Function to handle video or audio input
def process_input(input_file):
    try:
        audio_file = convert_audio(input_file)
        segments = split_audio(audio_file)
        filtered_dir = filter_audio(segments)
        output_file = combine_segments(filtered_dir, f"{input_file}.filtered.wav")
        shutil.rmtree(filtered_dir)
        output_format = input_file.split(".")[-1]

        if is_video(input_file):
            audio_aac_file = f"filtered-{input_file}.aac"
            ffmpeg.input(output_file).output(audio_aac_file, ar=44100, codec="aac").run()

            video_stream = ffmpeg.input(input_file).video
            audio_aac_stream = ffmpeg.input(audio_aac_file).audio
            
            merged_file = f"filtered-{input_file}.{output_format}"
            ffmpeg.output(video_stream, audio_aac_stream, merged_file, vcodec="copy", acodec="copy").run()

            os.remove(audio_aac_file)
            os.remove(output_file)
            os.remove(audio_file)
            os.rename(merged_file, input_file)

            return input_file
        else:
            ffmpeg.input(output_file).output(f"filtered-{input_file}.{output_format}", ac=1, ar=16000).run()

            os.rename(f"filtered-{input_file}.{output_format}", input_file)
            os.remove(output_file)
            os.remove(audio_file)

            return input_file
    except Exception as e:
        log_error(f"Error occurred during processing: {str(e)}")
        return None

# Streamlit UI
st.title("Audio Enhancement with Deep Filter")

uploaded_file = st.file_uploader("Upload a file", type=["mp4", "wav", "mp3", "aac", "m4a", "flac", "ogg", "opus", "wma", "webm", "mkv"])

if uploaded_file is not None:
    try:
        file_details = {"FileName": uploaded_file.name, "FileType": uploaded_file.type, "FileSize": uploaded_file.size}
        st.write(file_details)

        if st.button("Process File"):
            # generate a random file name to save the uploaded file
            file_path = f"temp-{str(uuid.uuid4())[:8]}.{uploaded_file.name.split('.')[-1]}"

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            output_file_path = process_input(file_path)

            if output_file_path and os.path.exists(output_file_path):
                data = open(output_file_path, "rb").read()
                os.remove(file_path)

                st.success("File processed successfully!")
                st.download_button(label="Download Processed File", 
                                    data=data,
                                    file_name="filtered-" + uploaded_file.name)
            else:
                st.error("File processing failed.")
    except Exception as e:
        log_error(f"Error occurred during file processing: {str(e)}")