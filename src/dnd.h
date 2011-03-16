// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_DND_H
#define __FCMAN_DND_H


// Requirements
#include <wx/defs.h>
#include <wx/dataobj.h>
#include <wx/dnd.h>
#include <wx/dynarray.h>
#include <wx/string.h>


class WXDLLIMPEXP_CORE wxTreeItemId;

class MainWindow;


// Files data object
class FilesDataObject : public wxCustomDataObject
{
public:
    FilesDataObject();

    void SetFileItems(const wxArrayInt& items);
    wxArrayInt GetFileItems() const;

    bool IsOk() const;
    void Clear();
};


// Directory data object
class DirectoryDataObject : public wxCustomDataObject
{
public:
    DirectoryDataObject();

    void SetDirectoryItem(const wxTreeItemId& item);
    wxTreeItemId GetDirectoryItem() const;

    bool IsOk() const;
    void Clear();
};

// Drop target
class DropTarget : public wxDropTarget
{
public:
    DropTarget(MainWindow* window);

    bool OnDrop(wxCoord x, wxCoord y);
    wxDragResult OnData(wxCoord x, wxCoord y, wxDragResult def);

private:
    void Reset();

    MainWindow* m_window;

    FilesDataObject* m_files;
    DirectoryDataObject* m_dir;
};



#endif // Header guard



