import wx

class AScrolledWindow(wx.ScrolledWindow):
    def __init__(self, parent):
        self.parent = parent
        wx.ScrolledWindow.__init__(self, parent, -1, style=wx.TAB_TRAVERSAL)
        self.gb = wx.GridBagSizer(vgap=0, hgap=0)    
        self.SetSizer(self.gb)
        fontsz = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT).GetPixelSize()
        self.SetScrollRate(fontsz.x, fontsz.y)
        self.EnableScrolling(True,True)

    def TextListener(self, event):
        for i, label in enumerate(self._labels):
            font = label.GetFont()
            if event.Id == label.Id:
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                if self.clickEvent is not None:
                    self.clickEvent(i)
            else:
                font.SetWeight(wx.FONTWEIGHT_NORMAL)
            label.SetFont(font)
        
    def addText(self, arr, clickEvent=None):
        self.gb.Clear(True)
        self.clickEvent=clickEvent
        self._labels = []
        for i, arr_item in enumerate(arr):
            label = wx.StaticText(self, label=arr_item)
            label.Bind(wx.EVT_LEFT_DOWN, self.TextListener, id=label.Id)
            self.gb.Add(label, (i,1), (0,0))
            self._labels.append(label)            
        self.OnInnerSizeChanged()
            
    def OnInnerSizeChanged(self):
        w,h = self.gb.GetMinSize()
        self.SetVirtualSize((w,h))
