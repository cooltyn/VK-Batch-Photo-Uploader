import json, os, datetime
import vk_api
import Tkinter as tk
import tkFileDialog as filedialog
from pathlib import Path
import tempfile
import os
from Crypto.Cipher import AES
import base64


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
    files = list(filedialog.askopenfilenames())
    total_count=len(files)
    total_loaded=0    
    print('%.i files is selected for uploading' %total_count)

    upload = vk_api.VkUpload(vk_session)

    for file in files:
        try:
            photo = upload.photo(
                file,
                album_id=album['id']
            )
        except BaseException as e:
            print ('Uploading error: '+file)
            error_files.append(file)
        else:
            total_loaded+=1        
            print('Uploaded %.i/%.i files' %(total_loaded,total_count))
    
    if len(error_files):
        print ('Not uploaded %.i/%.i files:' %(total_count-total_loaded,total_count))
        for file in error_files:            
            print (os.path.basename(file))
    
    raw_input('Done, press Enter to exit ')
        
main()
