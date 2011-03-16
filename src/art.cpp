// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/artprov.h>
#include <wx/log.h>

#include "app.h"
#include "art.h"


// Get the main icon
wxIconBundle Art::GetMainIcons()
{
    wxLogNull nolog;
    wxIconBundle bundle;

    Application& app = wxGetApp();

    bundle.AddIcon(wxIcon(app.GetPixmapDataPath(wxT("mainicon16.xpm"))));
    bundle.AddIcon(wxIcon(app.GetPixmapDataPath(wxT("mainicon32.xpm"))));
    bundle.AddIcon(wxIcon(app.GetPixmapDataPath(wxT("mainicon48.xpm"))));
    bundle.AddIcon(wxIcon(app.GetPixmapDataPath(wxT("mainicon64.xpm"))));
    
    return bundle;
}

// Folder icon
wxIcon Art::GetFolderIcon()
{
    return wxArtProvider::GetIcon(wxART_FOLDER);
}

// Folder icon
wxIcon Art::GetFileIcon()
{
    return wxArtProvider::GetIcon(wxART_NORMAL_FILE);
}

// Error icon
wxIcon Art::GetErrorIcon()
{
    return wxArtProvider::GetIcon(wxART_ERROR);
}

