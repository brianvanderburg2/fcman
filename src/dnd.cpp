// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/dataobj.h>
#include <wx/datetime.h>
#include <wx/dnd.h>
#include <wx/log.h>
#include <wx/string.h>
#include <wx/treectrl.h>

#include "dnd.h"
#include "mainwnd.h"


// Construct unique data object name
static wxString GetDataFormat(const wxString& format)
{
    static unsigned long magic = 0;

    if(magic == 0)
    {
        magic = wxDateTime::Now().GetAsDOS();
        if(magic == 0)
        {
            magic++;
        }
    }

    return wxString::Format(wxT("%lu"), magic) + format;
}


// Files data object
//----------------------------------------------------------------------------

static int gs_fileItemsCounter = 0;
static wxArrayInt gs_fileItems;

// Constructor
FilesDataObject::FilesDataObject()
{
    SetFormat(GetDataFormat(wxT("File")));
    Clear();
}

// Set data
void FilesDataObject::SetFileItems(const wxArrayInt& items)
{
    gs_fileItemsCounter++;
    gs_fileItems = items;

    SetData(sizeof(int), &gs_fileItemsCounter);
}

// Get data
wxArrayInt FilesDataObject::GetFileItems() const
{
    if(!IsOk())
        return wxArrayInt();

    return gs_fileItems;
}

// Is it okay
bool FilesDataObject::IsOk() const
{
    if(GetSize() != sizeof(int))
        return false;

    int* data = static_cast<int*>(GetData());
    if(!data || *data != gs_fileItemsCounter)
        return false;

    return true;
}

// Clear
void FilesDataObject::Clear()
{
    int data = -1;

    gs_fileItemsCounter = 0;
    gs_fileItems.Clear();
    SetData(sizeof(int), &data);
}


// Directory data object
//----------------------------------------------------------------------------

static int gs_dirItemCounter = 0;
static wxTreeItemId gs_dirItem;

// Constructor
DirectoryDataObject::DirectoryDataObject()
{
    SetFormat(GetDataFormat(wxT("Dir")));
    Clear();
}

// Set data
void DirectoryDataObject::SetDirectoryItem(const wxTreeItemId& item)
{
    gs_dirItemCounter++;
    gs_dirItem = item;

    SetData(sizeof(int), &gs_dirItemCounter);
}

// Get data
wxTreeItemId DirectoryDataObject::GetDirectoryItem() const
{
    if(!IsOk())
        return wxTreeItemId();

    return gs_dirItem;
}

// Is ok
bool DirectoryDataObject::IsOk() const
{
    if(GetSize() != sizeof(int))
        return false;

    int *data = static_cast<int*>(GetData());
    if(!data || *data != gs_dirItemCounter)
        return false;

    return true;
}

// Clear
void DirectoryDataObject::Clear()
{
    int data = -1;

    gs_dirItemCounter = 0;
    gs_dirItem = wxTreeItemId();
    SetData(sizeof(int), &data);
}


// Drop target
//----------------------------------------------------------------------------

// Constructor
DropTarget::DropTarget(MainWindow* window) :
    m_window(window),
    m_files(NULL),
    m_dir(NULL)
{
    Reset();
}

// Allow dropping
bool DropTarget::OnDrop(wxCoord WXUNUSED(x), wxCoord WXUNUSED(y))
{
    return true;
}

// Do work
wxDragResult DropTarget::OnData(wxCoord x, wxCoord y, wxDragResult WXUNUSED(def))
{
    if(!GetData())
        return wxDragNone;

    // File object?
    if(m_files->IsOk())
    {
        wxArrayInt files = m_files->GetFileItems();
        Reset();

        if(m_window->DropFiles(x, y, files))
            return wxDragMove;
        return wxDragNone;
    }

    // Directory object?
    if(m_dir->IsOk())
    {
        wxTreeItemId dir = m_dir->GetDirectoryItem();
        Reset();

        if(m_window->DropDirectory(x, y, dir))
            return wxDragMove;
        return wxDragNone;
    }

    Reset();
    return wxDragNone;
}

// Reset data
void DropTarget::Reset()
{
    m_files = new FilesDataObject();
    m_dir = new DirectoryDataObject();

    wxDataObjectComposite* comp = new wxDataObjectComposite();
    comp->Add(m_files);
    comp->Add(m_dir);

    SetDataObject(comp);
}


