import json, os, datetime, tempfile, base64, sys
import vk_api
import Tkinter as tk
import tkFileDialog as filedialog
from pathlib import Path
from time import time
from Crypto.Cipher import AES


secret_key = 'keiDMEkIiisDkGEf'
cipher = AES.new(secret_key,AES.MODE_ECB)
login_file=os.path.join(tempfile.gettempdir(), 'vk_uploader_login.dat')

def safeprint(text):
    print (text.encode(sys.stdout.encoding, errors='ignore'))

def encode(text):
    return base64.b64encode(cipher.encrypt(text.rjust(32)))

def decode(text):
    try:
        decoded_text = cipher.decrypt(base64.b64decode(text)).strip()
    except BaseException as e:
        return text
    else:
        return decoded_text

def check_login_file():
    if Path(login_file).is_file():
        with open(login_file, 'r') as file:
            pair = ask_password(json.load(file))
    else:
       pair = None
    return pair

def ask_password(pair):
    use_password = raw_input('Use saved password for login '+decode(pair['login'])+'? [y/n] ')
    if use_password in ['y','Y']:
        return pair
    elif use_password in ['n','N']:
        return None
    else:
        return ask_password(pair)

def try_to_login(pair):
    e = None
    while True:
        try:
            if pair is None or e is not None:
                pair = input_password()
            vk_session = vk_api.VkApi(decode(pair['login']), decode(pair['password']))
            vk_session.auth()
        except BaseException as e:
            print (e)
        else:
            return vk_session

def input_password():
    pair = {
        'login': None,
        'password': None
    }
    pair['login'] = encode(raw_input('Enter login: '))
    pair['password'] = encode(raw_input('Enter password: '))
    with open(login_file, 'w') as file:
        json.dump(pair, file)
    return pair

def get_group_info(group):
    return group['name']

def get_album_info(album):
    return album['title']+', '+str(album['size'])+' photos, created '+datetime.datetime.fromtimestamp(album['created']).strftime('%d.%m.%Y %H:%M')

def print_groups(groups):
    print ('Groups list:')
    for i, group in enumerate(groups['items']):        
        safeprint (str(i)+': '+get_group_info(group))
        
def select_group(groups):
    while True:
        try:
            group = groups['items'][int(raw_input('Enter group number to upload photos: '))]
        except BaseException as e:
            print ('Error with selecting group')
        else:
            safeprint ('Selected group: '+get_group_info(group))
            return group        

def select_album(vk, group_id):    
    try:
        if group_id is None:
            albums = vk.photos.getAlbums()
        else:
            albums = vk.photos.getAlbums(owner_id=-group_id)
            albums['items'] = [album for album in albums['items'] if album['can_upload'] is 1]
        if len(albums['items']) is 0:
            raise Exception()
    except BaseException as e:
        print ('Error, no available albums')
        return None
    
    print ('Albums list:')      
    for i, album in enumerate(albums['items']):
        safeprint (str(i)+': '+get_album_info(album))
    
    while True:
        try:
            album = albums['items'][int(raw_input('Enter album number to upload photos: '))]
        except BaseException as e:
            print ('Error with selecting album')
        else:
            safeprint ('Selected album: '+get_album_info(album))
            return album

def select_files():
    root = tk.Tk()
    root.withdraw()
    files = []
    filesize_total = float(0)    
    for file in filedialog.askopenfilenames():
        filesize=int(os.path.getsize(file))
        filesize_total+=filesize
        files.append([
            file,
            filesize
        ])
    print ('%.0f files is selected for uploading (%.1f MB)' %(len(files), filesize_total/(1024*1024)))
    return files, filesize_total

def upload_photos(files, group_id, album_id, upload, filesize_total):
    files_total = len(files)
    files_loaded = 0
    filesize_loaded = 0
    error_files = []
    time_start = time()
    for file in files:
        try:
            filesize_loaded+=file[1]
            photo = upload.photo(
                file[0],
                album_id = album_id,
                group_id = group_id
            )
        except BaseException as e:
            error_files.append(file)
            print ('Uploading error: '+file[0])
        else:
            files_loaded += len(photo)
            time_runned = time()-time_start
            print ('Uploaded %.i/%.i files, %.1f minutes left' %(files_loaded, files_total, (time_runned*filesize_total/filesize_loaded-time_runned)/60))

    if len(error_files):
        print ('Not uploaded %.i/%.i files:' %(files_total-files_loaded,files_total))
        for file in error_files:
            print (os.path.basename(file[0]))
    
    return (time()-time_start)/60
        
def main():
    print ('Welcome to VK Batch Photo Uploader!')
    vk_session = try_to_login(check_login_file())        
    vk = vk_session.get_api()
    user = vk.users.get()[0]
    groups = vk.groups.get(extended=1)    
    groups['items'].insert(0, {'name': (user['first_name']+' '+user['last_name']+' (yourself account)'), 'id': None})
    print_groups(groups)
    album = None
    while album is None:
        group = select_group(groups)
        album = select_album(vk, group['id'])
        
    files = []
    while len(files) is 0:
        files, filesize_total = select_files()
        
    elapsed_time = upload_photos(files, group['id'], album['id'], vk_api.VkUpload(vk_session), filesize_total)
    raw_input('Done in %.1f minutes, press Enter to exit ' %elapsed_time)

main()
