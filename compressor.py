import modwall; modwall.check()

import os
import winreg
import win32security
import getpass
import time

from math import ceil
from tqdm import tqdm
from zipfile import ZipFile
from threading import Thread

def get_beatmap_folder() -> str:
    songs_folder: str = os.path.expandvars("%userprofile%").replace("\\", "/") + "/AppData/Local/osu!/Songs/"

    sid = win32security.LookupAccountName(None, getpass.getuser())[0]
    key_path = win32security.ConvertSidToStringSid(sid) + "_Classes\\osustable.File.osk\\Shell\\Open\\Command"
    try:
        key = winreg.OpenKey(winreg.HKEY_USERS, key_path)

        songs_folder: str = winreg.EnumValue(key, 0)[1]
        songs_folder = songs_folder.split('\"')[1].replace("osu!.exe", "Songs\\")

        key.Close()
    except OSError:
        pass

    print("Songs folder: " + songs_folder)
    usr_input = input("Enter your Songs folder path (leave empty if above path is correct): ")
    if usr_input != "":
        songs_folder = usr_input
    
    return songs_folder.replace("\\", "/")  # Ensure forward slashes for consistency

def count_files(directory):
    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)
    return file_count
    
def calculate_total_size(folder: str) -> int:
    bar = tqdm(
        desc="Calculating folder size..............",
        total=count_files(folder),
        unit="files",
        unit_scale=True,
    )

    total_size = 0
    for root, _, files in os.walk(folder):
        for f in files:
            fp = os.path.join(root, f)
            total_size += os.path.getsize(fp)
            bar.update()

    return total_size

def compress_beatmaps(songs_folder: str, beatmaps: list[str], filename: str):
    with ZipFile(filename, "w") as zip:
        for i in tqdm(
            range(len(beatmaps)),
            desc=f"Compressing into {filename}..............",
            unit="beatmaps",
        ):
            beatmap_path = os.path.join(songs_folder, beatmaps[i])
            for root, _, files in os.walk(beatmap_path):
                for f in files:
                    fp = os.path.join(root, f)
                    zip.write(fp)

def compress(songs_folder: str, beatmaps: list[str], file_count: int) -> None:
    ratio = ceil(len(beatmaps)/file_count)
    tasks: list[Thread] = []
    for i in range(file_count):
        file_out = f"Pack_#{i+1}.zip"
        start_index = ratio*i
        end_index = start_index + ratio + 1
        if (i == file_count - 1):
            end_index = len(beatmaps)
        t = Thread(target=compress_beatmaps, daemon = True, args=[
                                            songs_folder,
                                            beatmaps[start_index : end_index],
                                            file_out])
        t.start()
        tasks.append(t)

    def has_live_threads(threads: list[Thread]) -> bool:
        for thread in threads:
            if thread.is_alive():
                return True
        return False
    
    try:
        while has_live_threads(tasks):
            time.sleep(0.1)
    except KeyboardInterrupt:
        exit(0)

if __name__ == "__main__":
    songs_folder = get_beatmap_folder()

    if not os.path.exists(songs_folder):
        print("Songs folder does not exist. Exiting.")
        exit(1)
    
    beatmaps = os.listdir(songs_folder)
    print(f"Found {len(beatmaps)} beatmaps in the Songs folder.")

    total_size = calculate_total_size(songs_folder) / (1024 * 1024)
    print(f"Total size of beatmaps: {total_size:.2f} MB")

    try:
        file_count = int(input(f"Enter numebr of zip files after compress (integer, 0 < n < {ceil(total_size / 1024)}): "))
        file_count = min(ceil(total_size / 1024), max(1, file_count))
    except ValueError:
        file_count = ceil(total_size / 1024)
    compress(songs_folder, beatmaps, file_count)