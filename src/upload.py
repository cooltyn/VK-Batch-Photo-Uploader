import json, os, datetime, tempfile, base64
import vk_api
import Tkinter as tk
import tkFileDialog as filedialog
from pathlib import Path
from time import time
from Crypto.Cipher import AES

secret_key = 'keiDMEkIiisDkGEf'
cipher = AES.new(secret_key,AES.MODE_ECB)
login_file=os.path.join(tempfile.gettempdir(), 'vk_uploader_login.dat')

def encode(text):
    return base64.b64encode(cipher.encrypt(text.rjust(32)))

def decode(text):
    return cipher.decrypt(base64.b64decode(text)).strip()

def get_album_info(album):
    return album['title']+', '+str(album['size'])+' photos, created '+datetime.datetime.fromtimestamp(album['created']).strftime('%d.%m.%Y %H:%M')

def ask_password(pair):
    use_password=raw_input('Use saved password for login '+decode(pair['login'])+'? [y/n]')
    if use_password in ['y','Y']:
        return pair
    elif use_password in ['n','N']:
        return False
    else:
        return ask_password(pair)

def input_password():
    pair={
        'login':None,
        'password':None
    }
    pair['login']=encode(raw_input('Enter login: '))
    pair['password']=encode(raw_input('Enter password: '))
    with open(login_file, 'w') as file:
        json.dump(pair, file)
    return pair
        
def main():
    pair=False
    need_to_login=True
    need_to_select_album=True
    login_error=False
    error_files=[]

    print ('Welcome to VK Batch Photo Uploader!')
    
    if Path(login_file).is_file():
        with open(login_file, 'r') as file:
            pair=ask_password(json.load(file))
    
    while need_to_login:
        try:
            if pair is False or login_error is True:
                pair=input_password()
            vk_session = vk_api.VkApi(decode(pair['login']), decode(pair['password']))
            vk_session.auth()
        except BaseException as e:
            print(e)
            login_error=True
        else:
            need_to_login=False
    
    vk = vk_session.get_api()
    upload = vk_api.VkUpload(vk_session)
    albums=vk.photos.getAlbums()

    print ('Albums list:')
    for i, album in enumerate(albums['items']):
        print (str(i)+': '+get_album_info(album))    

    while need_to_select_album:
        try:
            album = albums['items'][int(input('Enter album number to upload photos: '))]
        except BaseException as e:
            print ('Error with selecting album')
        else:
            need_to_select_album=False
            print('Selected album: '+get_album_info(album))
    
    root = tk.Tk()
    root.withdraw()
    files=[]
    filesize_total=float(0)
    filesize_loaded=0
    for file in filedialog.askopenfilenames():
        filesize=int(os.path.getsize(file))
        filesize_total+=filesize
        files.append([
            file,
            filesize
        ])
    
    files_total=len(files)
    files_loaded=0
    print('%.i files is selected for uploading (%.2f MB)' %(files_total, filesize_total/(1024*1024)))
    batch_size=1
    files=[files[i:i+batch_size] for i in xrange(0, len(files), batch_size)]
    time_start=time()
    
    for files_chunk in files:
        try:
            files_tmp=[]
            for file in files_chunk:
                files_tmp.append(file[0])
                filesize_loaded+=file[1]
            photo = upload.photo(
                files_tmp,
                album_id=album['id']
            )
        except BaseException as e:
            error_files.append(files_chunk[0])
            if batch_size is 1:
                print ('Uploading error: '+files_chunk[0][0])
            else:
                print ('Uploading error')
        else:
            files_loaded+=len(photo)
            time_runned=time()-time_start
            print('Uploaded %.i/%.i files, %.1f minutes left' %(files_loaded, files_total, (time_runned*filesize_total/filesize_loaded-time_runned)/60))

    if len(error_files):
        print ('Not uploaded %.i/%.i files:' %(files_total-files_loaded,files_total))
        if batch_size is 1:
            for file in error_files:
                print (os.path.basename(file[0]))
   
    raw_input('Done in %.1f minutes, press Enter to exit ' %((time()-time_start)/60))


main()
