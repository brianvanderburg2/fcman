// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_MAINWND_H
#define __FCMAN_MAINWND_H


// Requirements
#include <wx/defs.h>
#include <wx/dynarray.h>
#include <wx/frame.h>


class WXDLLIMPEXP_CORE wxPanel;
class WXDLLIMPEXP_CORE wxTextCtrl;
class WXDLLIMPEXP_CORE wxTreeItemId;
class WXDLLIMPEXP_CORE wxTreeEvent;
class WXDLLIMPEXP_CORE wxListEvent;

template <typename T> class TreeCtrl;
template <typename T> class ListCtrl;

class EditPanel;
class DropTarget;
class Log;

class Collection;
class Directory;
class File;
class Node;


// Main window
class MainWindow : public wxFrame
{
public:
    // ctor/dtor
    MainWindow();
    ~MainWindow();

    // Window events
    void OnClose(wxCloseEvent& evt);

    // Menu events
    void OnFileNew(wxCommandEvent& evt);
    void OnFileOpen(wxCommandEvent& evt);
    void OnFileSave(wxCommandEvent& evt);
    void OnFileClose(wxCommandEvent& evt);
    void OnFileExit(wxCommandEvent& evt);

    void OnHelpContents(wxCommandEvent& evt);
    void OnHelpAbout(wxCommandEvent& evt);
    void OnHelpClearLog(wxCommandEvent& evt);

    // Directory events
    void OnDirBeginDrag(wxTreeEvent& evt);
    void OnDirBeginLabelEdit(wxTreeEvent& evt);
    void OnDirEndLabelEdit(wxTreeEvent& evt);
    void OnDirItemCollapsed(wxTreeEvent& evt);
    void OnDirItemExpanding(wxTreeEvent& evt);
    void OnDirSelChanged(wxTreeEvent& evt);
    void OnDirKeyDown(wxTreeEvent& evt);
    void OnDirPopupMenu(wxTreeEvent& evt);

    // File events
    void OnFileBeginDrag(wxListEvent& evt);
    void OnFileEndLabelEdit(wxListEvent& evt);
    void OnFileItemSelected(wxListEvent& evt);
    void OnFileItemDeselected(wxListEvent& evt);
    void OnFileKeyDown(wxListEvent& evt);
    void OnFilePopupMenu(wxListEvent& evt);

    // Actions
    void OnActionNewDir(wxCommandEvent& evt);
    void OnActionVerifySanity(wxCommandEvent& evt);
    void OnActionAddNewItems(wxCommandEvent& evt);
    void OnActionRenameMissingItems(wxCommandEvent& evt);
    void OnActionRemoveMissingItems(wxCommandEvent& evt);
    void OnActionCalculateChecksums(wxCommandEvent& evt);
    void OnActionVerifyChecksums(wxCommandEvent& evt);
    void OnActionMarkDirty(wxCommandEvent& evt);

    // Drag and drop functions
    bool DropFiles(wxCoord x, wxCoord y, const wxArrayInt& files);
    bool DropDirectory(wxCoord x, wxCoord y, const wxTreeItemId& dir);

    // Open file (called at startup if command line file specified)
    bool OpenFile(const wxString& filename);
    
    // Real mode
    bool IsRealMode() const;

private:
    // Creation
    void CreateWidgets();
    void CreateMenus();

    // Helpers view
    void Reload();
    bool QueryClose();

    // Directory methods
    bool MoveDirectory(const wxTreeItemId& source, const wxTreeItemId& target);
    bool RenameDirectory(const wxTreeItemId& item, const wxString& name);
    bool DeleteDirectory(const wxTreeItemId& item);

    void PopulateDirectory(const wxTreeItemId& item);
    void ClearDirectory(const wxTreeItemId& item);
    void MarkDirectory(const wxTreeItemId& item, Directory* dir = NULL);

    // File methods
    bool MoveFiles(const wxArrayInt& sources, const wxTreeItemId& target);
    bool RenameFile(long item, const wxString& name);
    bool DeleteFiles(const wxArrayInt& items);

    void PopulateFiles(const wxTreeItemId& item);
    void ClearFiles();
    void MarkFile(long item, File* file = NULL);

    wxArrayInt GetSelectedFiles();


    // Members
    wxPanel* m_dirPanel;
    TreeCtrl<Directory>* m_dirs;
    wxPanel* m_filePanel;
    ListCtrl<File>* m_files;
    EditPanel* m_editPanel;
    Log* m_log;
    Collection* m_collection;

DECLARE_EVENT_TABLE()
};



#endif // Header guard



