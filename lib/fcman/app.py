# This file is placed in the public domain.

""" This module contains the application class and entry point. """

from __future__ import with_statement

try:
    xrange
except:
    xrange = range

import wx

class App(wx.App):
    """ Main application class. """

    def OnInit(self):
        """ Initialize the application and create the main window. """

        frame = wx.Frame(None, wx.ID_ANY, "Title")

        rowsizer = wx.BoxSizer(wx.VERTICAL)
        for i in xrange(5):
            colsizer = wx.BoxSizer(wx.HORIZONTAL)
            for j in xrange(5):
                button = wx.Button(frame, wx.ID_ANY, str((i + 1) * (j + 1)))
                colsizer.AddF(button, wx.SizerFlags(1).Expand().Border(wx.LEFT * int(j != 0)))
            rowsizer.AddF(colsizer, wx.SizerFlags(1).Expand().Border(wx.TOP * int(i != 0)))

        frame.SetSizerAndFit(rowsizer)
            

        self.SetTopWindow(frame)
        frame.Show(True)

        self.Bind(wx.EVT_BUTTON, self.OnButton, id=wx.ID_ANY)

        return True

    def OnButton(self, evt):
        wx.MessageBox(evt.GetEventObject().GetLabel())


def run():
    app = App()
    app.MainLoop()
    return 0

