# -*- coding: utf-8 -*-

import wx
import vk_api
import json, os, datetime, tempfile, base64, time, threading, sys, codecs
from pathlib import Path
from Crypto.Cipher import AES
from AScrolledWindow import AScrolledWindow

secret_key = 'keiDMEkIiisDkGEf'
cipher = AES.new(secret_key,AES.MODE_ECB)
login_file=os.path.join(tempfile.gettempdir(), 'vk_uploader_login.dat')

def encode(text):
    return base64.b64encode(cipher.encrypt(text.rjust(32)))

def decode(text):
    try:
        decoded_text = cipher.decrypt(base64.b64decode(text)).strip()
    except BaseException as e:
        return text
    else:
        return decoded_text

def startDaemon(func, args):
    thread = threading.Thread(target=func, args=args)
    thread.daemon = True
    thread.start()
    return thread

def pretty_time(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y %H:%M')

class Frame(wx.Frame):

    def __init__(self, *args, **kw):
        super(Frame, self).__init__(*args, **kw)

        if getattr(sys, 'frozen', False):
            extDataDir = sys._MEIPASS
        else:
            extDataDir = os.getcwd()
       
        icon = wx.Icon()
        icon.CopyFromBitmap(wx.Bitmap(os.path.join(extDataDir, 'icon.ico'), wx.BITMAP_TYPE_ANY))
        self.SetIcon(icon)

        self.buttons = {}
        self.group_id = False
        self.album_id = False
        self.files = []
        self.loading = False
        self.groups = {'items':[]}

        self.makeMenuBar()
        self.CreateStatusBar()
        
        topPanel = wx.Panel(self)        
        self.panelLeft = wx.Panel(topPanel)        
        self.panelRight = wx.Panel(topPanel)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.panelLeft, 1, wx.EXPAND)
        sizer.Add(self.panelRight, 1, wx.EXPAND)
        topPanel.SetSizer(sizer)
        
        self.panelLeft = self.addScroll(self.panelLeft)
        self.panelRight = self.addScroll(self.panelRight)        

    def addScroll(self, targ):
        targ.SetBackgroundColour('#ffffff')
        sizer = wx.BoxSizer(wx.VERTICAL)
        scroll = AScrolledWindow(targ)
        sizer.Add(scroll, 1, wx.EXPAND)
        targ.SetSizer(sizer)
        return scroll
            
    def makeMenuBar(self):
        accountMenu = wx.Menu()
        self.buttons['accountAddItem'] = accountMenu.Append(-1, "Add")
##        accountMenu.AppendSeparator()
        self.buttons['accountDeleteItem'] = accountMenu.Append(-1, "Delete")
        self.buttons['accountDeleteItem'].Enable(False)
        
        uploadMenu = wx.Menu()
        self.buttons['selectFilesItem'] = uploadMenu.Append(-1, "Select files")
        self.buttons['startUploadItem'] = uploadMenu.Append(-1, "Start upload")
        self.checkUploadBtn()
        
        helpMenu = wx.Menu()
        aboutItem = helpMenu.Append(wx.ID_ABOUT)

        menuBar = wx.MenuBar()
        menuBar.Append(accountMenu, "Account")
        menuBar.Append(uploadMenu, "Upload")
        menuBar.Append(helpMenu, "Help")
        self.SetMenuBar(menuBar)

        self.Bind(wx.EVT_MENU, self.addAccount, self.buttons['accountAddItem'])
        self.Bind(wx.EVT_MENU, self.deleteAccount,  self.buttons['accountDeleteItem'])
        self.Bind(wx.EVT_MENU, self.selectFiles,  self.buttons['selectFilesItem'])
        self.Bind(wx.EVT_MENU, self.startUpload,  self.buttons['startUploadItem'])
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)
        
    def deleteAccount(self, event):
        with wx.MessageDialog(self, 'Delete saved account '+decode(self.pair['login'])+'?', ' ', style=wx.YES_NO|wx.ICON_WARNING) as dlg:
            if dlg.ShowModal() == wx.ID_YES:
                os.remove(login_file)
                self.Close(True)
                   
    def ask(self, message='', default_value=''):
        with wx.TextEntryDialog(self, message, '', value=default_value, style=wx.OK) as dlg:
            dlg.ShowModal()
            return dlg.GetValue()

    def checkLoginFile(self):
        if Path(login_file).is_file():
            with open(login_file, 'r') as file:
                pair = json.load(file)
        else:
           pair = None
        return pair
    
    def initLogin(self):
        pair = self.checkLoginFile()
        if pair is not None:
            self.try_to_login(pair)

    def try_to_login(self, pair):
        try:
            vk_session = vk_api.VkApi(decode(pair['login']), decode(pair['password']))
            vk_session.auth()
        except BaseException as e:
            self.buttons['accountDeleteItem'].Enable(False)
            self.SetStatusText('Error: '+str(e))
        else:
            self.buttons['accountDeleteItem'].Enable(True)            
            self.pair = pair
            self.vk_session = vk_session
            self.vk = vk_session.get_api()
            self.user = self.vk.users.get()[0]
            self.SetStatusText('Success login as '+self.user['first_name']+' '+self.user['last_name'])
            self.upload = vk_api.VkUpload(vk_session)
            self.printGroups()
            with open(login_file, 'w') as file:
                json.dump(pair, file)

    def addAccount(self, event):
        login = encode(self.ask(message = 'Enter Login'))
        password = encode(self.ask(message = 'Enter Password'))
        self.try_to_login({'login': login, 'password': password})
        
    def OnAbout(self, event):
        wx.MessageBox('VK Batch Photo Uploader 0.41 by cooltyn', ' ', wx.OK|wx.ICON_INFORMATION)

    def loadGroups(self, count, i):        
        tmp = self.vk.groups.get(extended=1, count=count, offset=count*i)['items']
        self.groups['items'].extend(tmp)
        if len(tmp) == count:
            i += 1
            self.loadGroups(count, i)
    
    def printGroups(self):                  
        self.loadGroups(1000, 0)
        self.groups['items'].insert(0, {'name': (self.user['first_name']+' '+self.user['last_name']), 'id': None})
        self.panelLeft.addText([group['name'] for group in self.groups['items']], clickEvent=self.groupClick)

    def groupClick(self, num):
        self.group_id = self.groups['items'][num]['id']
        self.album_id = False
        self.printAlbums(self.group_id)
        self.checkUploadBtn()
        
    def get_album_info(self, album):
        return album['title']+', '+str(album['size'])+' photos, created '+pretty_time(album['created'])

    def printAlbums(self, group_id):
        try:
            if group_id is None:
                self.albums = self.vk.photos.getAlbums()
            else:
                self.albums = self.vk.photos.getAlbums(owner_id=-group_id)
                self.albums['items'] = [album for album in self.albums['items'] if album['can_upload'] is 1]
            if len(self.albums['items']) is 0:
                raise Exception()
        except BaseException as e:
            self.SetStatusText('Error, no available albums')
            self.albums={'items':[]}
        else:
            self.SetStatusText('')
        
        self.panelRight.addText([self.get_album_info(album) for album in self.albums['items']], clickEvent=self.albumClick)
        
    def albumClick(self, num):
        self.album_id=self.albums['items'][num]['id']        
        self.checkUploadBtn()
    
    def selectFiles(self, event):
        dialog = wx.FileDialog(self, "Choose a files", style=wx.FD_MULTIPLE, wildcard = "images|*.jpg;*.png;*.gif")
        if dialog.ShowModal() == wx.ID_OK:
            self.files = []
            self.filesize_total = float(0)    
            for file in dialog.GetPaths():
                filesize=int(os.path.getsize(file))
                self.filesize_total+=filesize
                self.files.append([
                    file,
                    filesize
                ])
            self.SetStatusText('%.0f files is selected for uploading (%.1f MB)' %(len(self.files), self.filesize_total/(1024*1024)))
        self.checkUploadBtn()
        
    def startUpload(self, event):
        startDaemon(self.uploadPhotos, (self.files, self.group_id, self.album_id, self.upload, self.filesize_total, self.SetStatusText))

    def checkUploadBtn(self):
        if self.group_id != False and self.album_id != False and len(self.files) != 0 and self.loading == False:
            self.buttons['startUploadItem'].Enable(True)
        else:
            self.buttons['startUploadItem'].Enable(False)

    def uploadPhotos(self, files, group_id, album_id, upload, filesize_total, logEvent):
        self.loading = True
        self.checkUploadBtn()
        for album in self.albums['items']:
            if album['id'] == album_id:
                message_text = album['title']
        for group in self.groups['items']:
            if group['id'] == group_id:
                message_text +=' in '+group['name']
        files_total = len(files)
        files_loaded = 0
        filesize_loaded = 0
        error_files = []
        time_start = time.time()        
        for file in files:
            try:
                time_runned = time.time()-time_start
                filesize_loaded+=file[1]
                photo = upload.photo(
                    file[0],
                    album_id = album_id,
                    group_id = group_id
                )
            except BaseException as e:
                error_files.append([
                    file[0],
                    pretty_time(time.time())
                ])
                logEvent('Uploading error: '+file[0])
            else:
                files_loaded += len(photo)                
                logEvent('Uploaded %.i/%.i files, %.1f minutes left' %(files_loaded, files_total, (time_runned*filesize_total/filesize_loaded-time_runned)/60))
        success_text = 'Uploaded %.i/%.i files in %.1f minutes to ' %(files_loaded, files_total, time_runned/60)
        if len(error_files):
            message_text += ', see errors in error_log.txt'
            error_text = ''
            for error in error_files:
                error_text += error[1]+' '+error[0]+'\r\n'
            try:
                with codecs.open('error_log.txt', 'w', 'utf-8') as file:
                    file.write(error_text)
            except BaseException as e:
                print 'error', e
                
        wx.MessageBox(success_text+message_text, 'VK Batch Uploader', wx.OK)
        self.loading = False
        self.checkUploadBtn()
        
        
if __name__ == '__main__':
    app = wx.App()
    screen_size=wx.GetDisplaySize()
    frm = Frame(None, title='VK Batch Photo Uploader', size=(screen_size[0]*0.7, screen_size[1]*0.7))
    frm.Show()
    frm.initLogin()
    app.MainLoop()
    
