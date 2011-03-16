// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include "config.h"

#include <vector>

#include <wx/defs.h>
#include <wx/artprov.h>
#include <wx/choicdlg.h>
#include <wx/dnd.h>
#include <wx/filedlg.h>
#include <wx/filefn.h>
#include <wx/filename.h>
#include <wx/frame.h>
#include <wx/imaglist.h>
#include <wx/intl.h>
#include <wx/log.h>
#include <wx/menu.h>
#include <wx/msgdlg.h>
#include <wx/sizer.h>
#include <wx/splitter.h>
#include <wx/textctrl.h>
#include <wx/textdlg.h>
#include <wx/utils.h>


#include "aboutdlg.h"
#include "app.h"
#include "art.h"
#include "dnd.h"
#include "mainwnd.h"

#include "actions.h"
#include "checksum.h"

#include "treectrl.h"
#include "listctrl.h"
#include "editpanel.h"
#include "log.h"

#include "collection/collection.h"


// Helper list control to autoresize column
//----------------------------------------------------------------------------
namespace
{

class AutoListCtrl : public ListCtrl<File>
{
public:
    AutoListCtrl(wxWindow* parent, wxWindowID id, long style);
    ~AutoListCtrl();

    void OnSize(wxSizeEvent& evt);

DECLARE_EVENT_TABLE();
};

// Event table
BEGIN_EVENT_TABLE(AutoListCtrl, ListCtrl<File>)
    EVT_SIZE(AutoListCtrl::OnSize)
END_EVENT_TABLE()

// Constructor
AutoListCtrl::AutoListCtrl(wxWindow* parent, wxWindowID id, long style) : 
    ListCtrl<File>(parent, id, style)
{
}

// Destructor
AutoListCtrl::~AutoListCtrl()
{
}

// Handle size
void AutoListCtrl::OnSize(wxSizeEvent& evt)
{
    wxRect r = GetClientRect();
    SetColumnWidth(0, r.width);
    evt.Skip();
}

} // private namespace


// Main window
//----------------------------------------------------------------------------

// Identifieers
enum
{
    ID_DIRS = wxID_HIGHEST + 1,
    ID_FILES,
    ID_LOG,

    ID_ACTION_NEW_DIR,
    ID_ACTION_VERIFY_SANITY,
    ID_ACTION_ADD_NEW,
    ID_ACTION_RENAME_MISSING,
    ID_ACTION_REMOVE_MISSING,
    ID_ACTION_CALCULATE_NEW,
    ID_ACTION_CALCULATE_ALL,
    ID_ACTION_VERIFY,
    ID_ACTION_CALCULATE_NEW_FILES,
    ID_ACTION_CALCULATE_ALL_FILES,
    ID_ACTION_VERIFY_FILES,
    ID_ACTION_MARK_DIRTY,
    ID_ACTION_MARK_CLEAN,
    ID_ACTION_MARK_DIRTY_FILES,
    ID_ACTION_MARK_CLEAN_FILES
};


// Event table
BEGIN_EVENT_TABLE(MainWindow, wxFrame)
    EVT_CLOSE(MainWindow::OnClose)

    EVT_MENU(wxID_NEW, MainWindow::OnFileNew)
    EVT_MENU(wxID_OPEN, MainWindow::OnFileOpen)
    EVT_MENU(wxID_SAVE, MainWindow::OnFileSave)
    EVT_MENU(wxID_CLOSE, MainWindow::OnFileClose)
    EVT_MENU(wxID_EXIT, MainWindow::OnFileExit)
    
    EVT_MENU(wxID_HELP_CONTENTS, MainWindow::OnHelpContents)
    EVT_MENU(wxID_ABOUT, MainWindow::OnHelpAbout)
    EVT_MENU(wxID_CLEAR, MainWindow::OnHelpClearLog)

    EVT_TREE_BEGIN_DRAG(ID_DIRS, MainWindow::OnDirBeginDrag)
    EVT_TREE_BEGIN_LABEL_EDIT(ID_DIRS, MainWindow::OnDirBeginLabelEdit)
    EVT_TREE_END_LABEL_EDIT(ID_DIRS, MainWindow::OnDirEndLabelEdit)
    EVT_TREE_ITEM_COLLAPSED(ID_DIRS, MainWindow::OnDirItemCollapsed)
    EVT_TREE_ITEM_EXPANDING(ID_DIRS, MainWindow::OnDirItemExpanding)
    EVT_TREE_SEL_CHANGED(ID_DIRS, MainWindow::OnDirSelChanged)
    EVT_TREE_KEY_DOWN(ID_DIRS, MainWindow::OnDirKeyDown)
    EVT_TREE_ITEM_MENU(ID_DIRS, MainWindow::OnDirPopupMenu)

    EVT_LIST_BEGIN_DRAG(ID_FILES, MainWindow::OnFileBeginDrag)
    EVT_LIST_END_LABEL_EDIT(ID_FILES, MainWindow::OnFileEndLabelEdit)
    EVT_LIST_ITEM_SELECTED(ID_FILES, MainWindow::OnFileItemSelected)
    EVT_LIST_ITEM_DESELECTED(ID_FILES, MainWindow::OnFileItemDeselected)
    EVT_LIST_KEY_DOWN(ID_FILES, MainWindow::OnFileKeyDown)
    EVT_LIST_ITEM_RIGHT_CLICK(ID_FILES, MainWindow::OnFilePopupMenu)

    EVT_MENU(ID_ACTION_NEW_DIR, MainWindow::OnActionNewDir)
    EVT_MENU(ID_ACTION_VERIFY_SANITY, MainWindow::OnActionVerifySanity)
    EVT_MENU(ID_ACTION_ADD_NEW, MainWindow::OnActionAddNewItems)
    EVT_MENU(ID_ACTION_RENAME_MISSING, MainWindow::OnActionRenameMissingItems)
    EVT_MENU(ID_ACTION_REMOVE_MISSING, MainWindow::OnActionRemoveMissingItems)
    EVT_MENU(ID_ACTION_CALCULATE_NEW, MainWindow::OnActionCalculateChecksums)
    EVT_MENU(ID_ACTION_CALCULATE_ALL, MainWindow::OnActionCalculateChecksums)
    EVT_MENU(ID_ACTION_VERIFY, MainWindow::OnActionVerifyChecksums)
    EVT_MENU(ID_ACTION_CALCULATE_NEW_FILES, MainWindow::OnActionCalculateChecksums)
    EVT_MENU(ID_ACTION_CALCULATE_ALL_FILES, MainWindow::OnActionCalculateChecksums)
    EVT_MENU(ID_ACTION_VERIFY_FILES, MainWindow::OnActionVerifyChecksums)
    EVT_MENU(ID_ACTION_MARK_DIRTY, MainWindow::OnActionMarkDirty)
    EVT_MENU(ID_ACTION_MARK_CLEAN, MainWindow::OnActionMarkDirty)
    EVT_MENU(ID_ACTION_MARK_DIRTY_FILES, MainWindow::OnActionMarkDirty)
    EVT_MENU(ID_ACTION_MARK_CLEAN_FILES, MainWindow::OnActionMarkDirty)
END_EVENT_TABLE()


// Constructor
MainWindow::MainWindow() :
    m_dirPanel(NULL),
    m_dirs(NULL),
    m_filePanel(NULL),
    m_files(NULL),
    m_editPanel(NULL),
    m_log(NULL),
    m_collection(NULL)
{
    wxFrame::Create(NULL, wxID_ANY, wxT(APP_DISPLAY_NAME));

    CreateWidgets();
    SetIcons(Art::GetMainIcons());
    Reload();
    Maximize();
}

// Destructor
MainWindow::~MainWindow()
{
}

// Close window
void MainWindow::OnClose(wxCloseEvent& evt)
{
    if(QueryClose())
        Destroy();
    else
        evt.Veto();
}

// New file
void MainWindow::OnFileNew(wxCommandEvent& WXUNUSED(evt))
{
    if(!QueryClose())
        return;

    wxString filename = wxFileSelector(_("New File"), wxEmptyString, wxT("collection.xml"),
        wxT("xml"), wxT("*"), wxFD_SAVE | wxFD_OVERWRITE_PROMPT, this);

    if(filename.IsEmpty())
        return;

    m_collection = Collection::New(filename);
    Reload();
}

// Open file
void MainWindow::OnFileOpen(wxCommandEvent& WXUNUSED(evt))
{
    if(!QueryClose())
        return;

    wxString filename = wxFileSelector(_("Open File"), wxEmptyString, wxT("collection.xml"),
        wxT("xml"), wxT("*"), wxFD_OPEN | wxFD_FILE_MUST_EXIST, this);

    if(filename.IsEmpty())
        return;

    OpenFile(filename);
}

// Save file
void MainWindow::OnFileSave(wxCommandEvent& WXUNUSED(evt))
{
    // If the user chooses to save, always save even if it is not dirty
    if(m_collection)
    {
        if(!m_collection->SaveFile())
        {
            ::wxLogError(_("An error occurred while saving the file."));
        }
    }
}

// Close file
void MainWindow::OnFileClose(wxCommandEvent& WXUNUSED(evt))
{
    QueryClose();
}

// Exit
void MainWindow::OnFileExit(wxCommandEvent& WXUNUSED(evt))
{
    if(QueryClose())
        Close();
}

// Help contents
void MainWindow::OnHelpContents(wxCommandEvent& WXUNUSED(evt))
{
    ::wxLaunchDefaultBrowser(wxGetApp().GetHelpFile());
}

// About
void MainWindow::OnHelpAbout(wxCommandEvent& WXUNUSED(evt))
{
    AboutDialog dlg(this);
    dlg.ShowModal();
}

// Clear log window
void MainWindow::OnHelpClearLog(wxCommandEvent& WXUNUSED(evt))
{
    m_log->Clear();
}

// Directory item starting drag
void MainWindow::OnDirBeginDrag(wxTreeEvent& evt)
{
    wxTreeItemId item = evt.GetItem();
    if(!item.IsOk() || item == m_dirs->GetRootItem())
    {
        evt.Veto();
        return;
    }

    DirectoryDataObject data;
    data.SetDirectoryItem(item);

    wxDropSource source(m_dirs);
    source.SetData(data);

    source.DoDragDrop(wxDrag_DefaultMove);
}

// Directory item starting label edit
void MainWindow::OnDirBeginLabelEdit(wxTreeEvent& evt)
{
    if(evt.GetItem() == m_dirs->GetRootItem())
        evt.Veto();
}

// Directory item ending label edit
void MainWindow::OnDirEndLabelEdit(wxTreeEvent& evt)
{
    if(evt.IsEditCancelled())
    {
        evt.Veto();
        return;
    }

    wxTreeItemId item = evt.GetItem();

    if(!RenameDirectory(item, evt.GetLabel()))
        evt.Veto();
}

// Directory item collapsed
void MainWindow::OnDirItemCollapsed(wxTreeEvent& evt)
{
    wxTreeItemId item = evt.GetItem();
    if(!item.IsOk())
        return;

    ClearDirectory(item);
}

// Directory item expanding
void MainWindow::OnDirItemExpanding(wxTreeEvent& evt)
{
    wxTreeItemId item = evt.GetItem();
    if(!item.IsOk())
        return;

    PopulateDirectory(item);
}

// Directory item changed
void MainWindow::OnDirSelChanged(wxTreeEvent& evt)
{
    wxTreeItemId item = evt.GetItem();
    if(!item.IsOk())
        return;

    PopulateFiles(item);
}
// Directory key pressed
void MainWindow::OnDirKeyDown(wxTreeEvent& evt)
{
    int code = evt.GetKeyCode();
    if(!(code == WXK_DELETE || code == WXK_NUMPAD_DELETE))
    {
        evt.Skip();
        return;
    }

    wxTreeItemId item = m_dirs->GetSelection();
    if(!item.IsOk() || item == m_dirs->GetRootItem())
        return;

    if(::wxMessageBox(_("Delete selected items?"), _("Question"), wxYES_NO | wxNO_DEFAULT) == wxNO)
        return;
    
    DeleteDirectory(item);
}

// Directory item popup menu
void MainWindow::OnDirPopupMenu(wxTreeEvent& WXUNUSED(evt))
{
    wxMenu* menu = new wxMenu();

    menu->Append(ID_ACTION_NEW_DIR, _("New Directory"));
    menu->AppendSeparator();

    menu->Append(ID_ACTION_VERIFY_SANITY, _("Verify Sanity"));
    menu->AppendSeparator();

    menu->Append(ID_ACTION_ADD_NEW, _("Add New Items"));
    menu->Append(ID_ACTION_RENAME_MISSING, _("Rename Missing Items"));
    menu->Append(ID_ACTION_REMOVE_MISSING, _("Remove Missing Items"));
    menu->AppendSeparator();

    menu->Append(ID_ACTION_CALCULATE_NEW, _("Calculate New Checksums"));
    menu->Append(ID_ACTION_CALCULATE_ALL, _("Calculate All Checksums"));
    menu->Append(ID_ACTION_VERIFY, _("Verify Checksums"));

    menu->AppendSeparator();
    menu->Append(ID_ACTION_MARK_DIRTY, _("Mark Dirty"));
    menu->Append(ID_ACTION_MARK_CLEAN, _("Mark Clean"));

    PopupMenu(menu);
    delete menu;
}

// File item starting drag
void MainWindow::OnFileBeginDrag(wxListEvent& evt)
{
    if(m_files->GetSelectedItemCount() < 1)
    {
        evt.Veto();
        return;
    }

    FilesDataObject data;
    data.SetFileItems(GetSelectedFiles());

    wxDropSource source(m_files);
    source.SetData(data);

    source.DoDragDrop(wxDrag_DefaultMove);
}

// File item ending a label edit
void MainWindow::OnFileEndLabelEdit(wxListEvent& evt)
{
    if(evt.IsEditCancelled())
    {
        evt.Veto();
        return;
    }

    if(!RenameFile(evt.GetIndex(), evt.GetLabel()))
        evt.Veto();
}

// File item selected
void MainWindow::OnFileItemSelected(wxListEvent& WXUNUSED(evt))
{
    if(m_files->GetSelectedItemCount() != 1)
    {
        m_editPanel->SetFile(NULL);
        return;
    }

    long item = m_files->GetFirstSelected();
    File* file = m_files->GetItemData(item);

    m_editPanel->SetFile(file);
}

// File item deselected
void MainWindow::OnFileItemDeselected(wxListEvent& WXUNUSED(evt))
{
    m_editPanel->SetFile(NULL);
}

// File item key down
void MainWindow::OnFileKeyDown(wxListEvent& evt)
{
    int code = evt.GetKeyCode();
    if(!(code == WXK_DELETE || code == WXK_NUMPAD_DELETE))
    {
        evt.Skip();
        return;
    }

    if(m_files->GetSelectedItemCount() < 1)
        return;

    if(::wxMessageBox(_("Delete selected items?"), _("Question"), wxYES_NO | wxNO_DEFAULT) == wxNO)
        return;
    
    DeleteFiles(GetSelectedFiles());
}

// File popup menu
void MainWindow::OnFilePopupMenu(wxListEvent& WXUNUSED(evt))
{
    wxMenu* menu = new wxMenu();

    menu->Append(ID_ACTION_CALCULATE_NEW_FILES, _("Calculate New Checksums"));
    menu->Append(ID_ACTION_CALCULATE_ALL_FILES, _("Calculate All Checksums"));
    menu->Append(ID_ACTION_VERIFY_FILES, _("Verify Checksums"));

    menu->AppendSeparator();
    menu->Append(ID_ACTION_MARK_DIRTY_FILES, _("Mark Dirty"));
    menu->Append(ID_ACTION_MARK_CLEAN_FILES, _("Mark Clean"));

    PopupMenu(menu);
    delete menu;
}

// Create a new directory item
void MainWindow::OnActionNewDir(wxCommandEvent& WXUNUSED(evt))
{
    wxTreeItemId item = m_dirs->GetSelection();
    if(!item.IsOk())
        return;

    Directory* container = m_dirs->GetItemData(item);
    if(!container)
        return;
    
    wxString name = ::wxGetTextFromUser(_("Name"), _("New Directory"), wxT("untitled"));
    if(!name.Len())
        return;
   
    m_editPanel->SetFile(NULL);

    // Add item
    Directory* dir = new Directory();
    dir->Rename(name);
    container->AddChild(dir);

    m_dirs->SetItemHasChildren(item, true);

    // Select it
    if(!m_dirs->IsExpanded(item))
    {
        m_dirs->Expand(item);

        wxTreeItemIdValue cookie = 0;
        wxTreeItemId child = m_dirs->GetFirstChild(item, cookie);
        while(child.IsOk())
        {
            Directory* childDir = m_dirs->GetItemData(child);
            if(childDir == dir)
            {
                m_dirs->SelectItem(child);
                break;
            }

            child = m_dirs->GetNextSibling(child);
        }
    }
    else
    {
        wxTreeItemId child = m_dirs->AppendItem(item, dir->GetName());
        m_dirs->SetItemData(child, dir);
        m_dirs->SetItemHasChildren(child, false);
        m_dirs->SelectItem(child);
        MarkDirectory(child, dir);
    }
}

// Verify sanity
void MainWindow::OnActionVerifySanity(wxCommandEvent& WXUNUSED(evt))
{
    wxTreeItemId item = m_dirs->GetSelection();
    if(!item.IsOk())
        return;

    Directory* dir = m_dirs->GetItemData(item);
    if(!dir)
        return;

    ActionCallback progress(this, m_log, _("Verifying sanity"));
    progress.SetProgressSkip(50);
    VerifySanity(dir, progress);
}

// Add new items
void MainWindow::OnActionAddNewItems(wxCommandEvent& WXUNUSED(evt))
{
    wxTreeItemId item = m_dirs->GetSelection();
    if(!item.IsOk())
        return;

    Directory* dir = m_dirs->GetItemData(item);
    if(!dir)
        return;

    m_editPanel->SetFile(NULL);

    ActionCallback progress(this, m_log, _("Adding new items items."));
    progress.SetProgressSkip(50);
    AddNewItems(dir, progress);

    PopulateDirectory(item);
    PopulateFiles(item);
}

// Rename missing items
void MainWindow::OnActionRenameMissingItems(wxCommandEvent& WXUNUSED(evt))
{
    wxTreeItemId item = m_dirs->GetSelection();
    if(!item.IsOk())
        return;

    Directory* dir = m_dirs->GetItemData(item);
    if(!dir)
        return;

    m_editPanel->SetFile(NULL);

    ActionCallback progress(this, m_log, _("Rename missing items."));
    progress.SetProgressSkip(50);
    RenameMissingItems(dir, progress);

    PopulateDirectory(item);
    PopulateFiles(item);
}

// Remove missing items
void MainWindow::OnActionRemoveMissingItems(wxCommandEvent& WXUNUSED(evt))
{
    wxTreeItemId item = m_dirs->GetSelection();
    if(!item.IsOk())
        return;

    Directory* dir = m_dirs->GetItemData(item);
    if(!dir)
        return;

    m_editPanel->SetFile(NULL);

    ActionCallback progress(this, m_log, _("Removing missing items."));
    progress.SetProgressSkip(50);
    RemoveMissingItems(dir, progress);

    PopulateDirectory(item);
    PopulateFiles(item);
}

// Calculate checksums
void MainWindow::OnActionCalculateChecksums(wxCommandEvent& evt)
{
    int id = evt.GetId();
    if(id == ID_ACTION_CALCULATE_NEW || id == ID_ACTION_CALCULATE_ALL)
    {
        wxTreeItemId item = m_dirs->GetSelection();
        if(!item.IsOk())
            return;

        Directory* dir = m_dirs->GetItemData(item);
        if(!dir)
            return;

        wxString type = ::wxGetSingleChoice(_("Select type"), _("Calculate checksum"),
            ChecksumCalculator::GetTypes(), this);
        if(type == wxEmptyString)
            return;

        m_editPanel->SetFile(NULL);

        ActionCallback progress(this, m_log, _("Calculating checksums."));
        progress.SetProgressSkip(50);

        CalculateChecksums(dir, progress, type, id == ID_ACTION_CALCULATE_ALL);
    }
    else if(id == ID_ACTION_CALCULATE_NEW_FILES || id == ID_ACTION_CALCULATE_ALL_FILES)
    {
        wxArrayInt selected = GetSelectedFiles();
        if(selected.Count() == 0)
            return;

        FileList files;
        for(size_t pos = 0; pos < selected.Count(); pos++)
        {
            File* file = m_files->GetItemData(selected[pos]);
            if(file)
                files.push_back(file);
        }
        
        wxString type = ::wxGetSingleChoice(_("Select type"), _("Calculate checksum"),
            ChecksumCalculator::GetTypes(), this);
        if(type == wxEmptyString)
            return;

        m_editPanel->SetFile(NULL);

        ActionCallback progress(this, m_log, _("Calculating checksums."));
        progress.SetProgressSkip(50);

        CalculateChecksums(files, progress, type, id == ID_ACTION_CALCULATE_ALL_FILES);
    }
}

// Verify checksums
void MainWindow::OnActionVerifyChecksums(wxCommandEvent& evt)
{
    int id = evt.GetId();
    if(id == ID_ACTION_VERIFY)
    {
        wxTreeItemId item = m_dirs->GetSelection();
        if(!item.IsOk())
            return;

        Directory* dir = m_dirs->GetItemData(item);
        if(!dir)
            return;

        m_editPanel->SetFile(NULL);

        ActionCallback progress(this, m_log, _("Verifying checksums."));
        progress.SetProgressSkip(50);

        VerifyChecksums(dir, progress);
    }
    else if(id == ID_ACTION_VERIFY_FILES)
    {
        wxArrayInt selected = GetSelectedFiles();
        if(selected.Count() == 0)
            return;

        FileList files;
        for(size_t pos = 0; pos < selected.Count(); pos++)
        {
            File* file = m_files->GetItemData(selected[pos]);
            if(file)
                files.push_back(file);
        }

        m_editPanel->SetFile(NULL);

        ActionCallback progress(this, m_log, _("Verifying checksums."));
        progress.SetProgressSkip(50);

        VerifyChecksums(files, progress);
    }
}

// Mark dirty or clean
void MainWindow::OnActionMarkDirty(wxCommandEvent& evt)
{
    int id = evt.GetId();

    bool dirty;
    if(id == ID_ACTION_MARK_DIRTY || id == ID_ACTION_MARK_DIRTY_FILES)
    {
        dirty = true;
    }
    else if(id == ID_ACTION_MARK_CLEAN || id == ID_ACTION_MARK_CLEAN_FILES)
    {
        dirty = false;
    }
    else
    {
        return;
    }

    FileList files;
    if(id == ID_ACTION_MARK_DIRTY || id == ID_ACTION_MARK_CLEAN)
    {
        wxTreeItemId item = m_dirs->GetSelection();
        if(!item.IsOk())
            return;

        Directory* dir = m_dirs->GetItemData(item);
        if(!dir)
            return;

        files = dir->GetFiles(true);
    }
    else if(id == ID_ACTION_MARK_DIRTY_FILES || id == ID_ACTION_MARK_CLEAN_FILES)
    {
        wxArrayInt selected = GetSelectedFiles();
        if(selected.Count() == 0)
            return;

        for(size_t pos = 0; pos < selected.Count(); pos++)
        {
            File* file = m_files->GetItemData(selected[pos]);
            if(file)
                files.push_back(file);
        }
    }

    m_editPanel->SetFile(NULL);

    ActionCallback progress(this, m_log, dirty ? _("Marking Dirty") : _("Marking Clean"));
    progress.SetProgressSkip(50);

    MarkDirty(files, progress, dirty);
}

// Handle file drop
bool MainWindow::DropFiles(wxCoord x, wxCoord y, const wxArrayInt& files)
{
    wxTreeItemId target;
    int flags = 0;

    target = m_dirs->HitTest(wxPoint(x, y), flags);
    if(target.IsOk() and files.Count() > 0)
    {
        return MoveFiles(files, target);
    }

    return false;
}

// Handle directory drop
bool MainWindow::DropDirectory(wxCoord x, wxCoord y, const wxTreeItemId& dir)
{
    wxTreeItemId target;
    int flags = 0;

    target = m_dirs->HitTest(wxPoint(x, y), flags);
    if(target.IsOk() and dir.IsOk())
    {
        return MoveDirectory(dir, target);
    }

    return false;
}

// Open a file
bool MainWindow::OpenFile(const wxString& filename)
{
    m_collection = Collection::Open(filename);
    if(!m_collection)
        wxLogError(_("An error occurred while loading the file."));
    else
        Reload();

    return (m_collection != NULL);
}


// Is real mode enabled
bool MainWindow::IsRealMode() const
{
    return ::wxGetKeyState(WXK_CONTROL);
}

// Create widgets
void MainWindow::CreateWidgets()
{
    wxBusyCursor busy;

    // Menus
    CreateMenus();

    // Splitters
    wxSplitterWindow* topSplitter = new wxSplitterWindow(this);
    topSplitter->SetMinimumPaneSize(10);

    wxSplitterWindow* midSplitter = new wxSplitterWindow(topSplitter);
    midSplitter->SetMinimumPaneSize(10);

    // Directory panel
    m_dirPanel = new wxPanel(midSplitter);
    wxImageList* dirImages = new wxImageList(16, 16);

    dirImages->Add(Art::GetFolderIcon());
    dirImages->Add(Art::GetErrorIcon());

    m_dirs = new TreeCtrl<Directory>(m_dirPanel, ID_DIRS,
        wxTR_EDIT_LABELS | wxTR_HAS_BUTTONS | wxTR_LINES_AT_ROOT | wxTR_SINGLE | wxBORDER_SUNKEN);
    m_dirs->AssignImageList(dirImages);

    wxBoxSizer* dirSizer = new wxBoxSizer(wxVERTICAL);
    dirSizer->Add(m_dirs, wxSizerFlags(1).Expand());
    m_dirPanel->SetSizer(dirSizer);

    // Drop target
    m_dirs->SetDropTarget(new DropTarget(this));

    // File panel
    m_filePanel = new wxPanel(midSplitter);
    wxImageList* fileImages = new wxImageList(16, 16);

    fileImages->Add(Art::GetFileIcon());
    fileImages->Add(Art::GetErrorIcon());

    m_files = new AutoListCtrl(m_filePanel, ID_FILES,
        wxLC_REPORT | wxLC_EDIT_LABELS | wxBORDER_SUNKEN | wxHSCROLL);
    m_files->InsertColumn(0, _("Name"));
    m_files->AssignImageList(fileImages, wxIMAGE_LIST_SMALL);

    m_editPanel = new EditPanel(m_filePanel);

    wxBoxSizer* fileSizer = new wxBoxSizer(wxVERTICAL);
    fileSizer->Add(m_files, wxSizerFlags(1).Expand().Border(wxBOTTOM));
    fileSizer->Add(m_editPanel, wxSizerFlags(1).Expand());
    m_filePanel->SetSizer(fileSizer);

    // Log
    m_log = new Log(topSplitter, ID_LOG);

    // Split
    midSplitter->SplitVertically(m_dirPanel, m_filePanel);
    midSplitter->SetSashGravity(0.5);

    topSplitter->SplitHorizontally(midSplitter, m_log);
    topSplitter->SetSashGravity(0.75);

    // Sizer
    wxBoxSizer* topSizer = new wxBoxSizer(wxVERTICAL);
    topSizer->Add(topSplitter, wxSizerFlags(1).Expand().Border());
    SetSizerAndFit(topSizer);
}

// Menu
void MainWindow::CreateMenus()
{
    wxMenuBar* menuBar = new wxMenuBar;

    // Collection menu
    wxMenu* collection = new wxMenu;

    collection->Append(wxID_NEW, _("&New"), _("Create a new collection."));
    collection->Append(wxID_OPEN, _("&Open"), _("Open an existing collection."));
    collection->Append(wxID_SAVE, _("&Save"), _("Save the current collection."));
    collection->AppendSeparator();
    collection->Append(wxID_CLOSE, _("&Close"), _("Close the current collection."));
    collection->Append(wxID_EXIT, _("E&xit"), _("Exit the program."));

    menuBar->Append(collection, _("&File"));

    // Help menu
    wxMenu* help = new wxMenu;

    //help->Append(wxID_HELP_CONTENTS, _("&Contents"), _("Show program help."));
    help->Append(wxID_ABOUT, _("&About"), _("Show information about the program."));
    help->AppendSeparator();
    help->Append(wxID_CLEAR, _("Clear Log"), _("Clear the log window."));

    menuBar->Append(help, _("&Help"));

    // Activate
    SetMenuBar(menuBar);
}

// Reload the view
void MainWindow::Reload()
{
    m_editPanel->SetFile(NULL);
    m_dirs->DeleteAllItems();
    m_files->DeleteAllItems();

    if(m_collection)
    {
        wxString title(wxT(APP_DISPLAY_NAME " - "));
        title = title + m_collection->GetFilename();

        SetTitle(title);
        m_dirPanel->Enable(true);
        m_filePanel->Enable(true);

        wxTreeItemId root = m_dirs->AddRoot(m_collection->GetFullPath(), 0);
        m_dirs->SetItemData(root, m_collection);
        m_dirs->SetItemHasChildren(root, m_collection->HasDirectories());

        m_dirs->SelectItem(root);
        PopulateFiles(root);
        m_dirs->Expand(root);
    }
    else
    {
        SetTitle(wxT(APP_DISPLAY_NAME));
        m_dirPanel->Enable(false);
        m_filePanel->Enable(false);
    }
}

// Query to close or not
bool MainWindow::QueryClose()
{
    if(!m_collection)
        return true;

    m_editPanel->SetFile(NULL);

    if(!m_collection->IsDirty())
    {
        m_collection->Close();
        m_collection = NULL;
        Reload();
        return true;
    }

    int result = ::wxMessageBox(_("Save changes to the file?"), _("Question"), wxYES_NO | wxCANCEL);
    if(result == wxCANCEL)
        return false;

    if(result == wxYES)
    {
        if(m_collection->SaveFile() == false)
        {
            wxLogError(_("An error occurred while saving the file."));
            return false;
        }
    }

    m_collection->Close();
    m_collection = NULL;
    Reload();
    return true;
}

// Move a directory item
bool MainWindow::MoveDirectory(const wxTreeItemId& source, const wxTreeItemId& target)
{
    Directory* sourceDir = m_dirs->GetItemData(source);
    Directory* targetDir = m_dirs->GetItemData(target);

    if(!sourceDir || !targetDir)
        return false;

    m_editPanel->SetFile(NULL);

    // Real mode
    if(IsRealMode())
    {
        if(!sourceDir->CanMove(targetDir))
            return false;

        wxFileName sourcefn(sourceDir->GetFullPath(), wxEmptyString);
        wxFileName targetfn(targetDir->GetFullPath(), wxEmptyString);

        if(sourcefn.DirExists() && targetfn.DirExists())
        {
            wxFileName newname(targetfn.GetPath(), wxEmptyString);
            newname.AppendDir(sourcefn.GetDirs().Last());

            if(!::wxRenameFile(sourcefn.GetFullPath(), newname.GetFullPath(), false))
            {
                // wxRenameFile logs error
                return false;
            }
        }
        else
        {
            return false;
        }
    }

    // Get parent information
    wxTreeItemId parent = m_dirs->GetItemParent(source);
    Directory* parentDir = m_dirs->GetItemData(parent);

    // Do the move
    if(!sourceDir->Move(targetDir))
        return false;

    m_dirs->Delete(source);
    m_dirs->SetItemHasChildren(parent, parentDir->HasDirectories());
    m_dirs->SetItemHasChildren(target, true);

    // Add to the tree item and select
    if(!m_dirs->IsExpanded(target))
    {
        m_dirs->Expand(target);

        wxTreeItemIdValue cookie = 0;
        wxTreeItemId child = m_dirs->GetFirstChild(target, cookie);
        while(child.IsOk())
        {
            Directory* childDir = m_dirs->GetItemData(child);
            if(childDir == sourceDir)
            {
                m_dirs->SelectItem(child);
                break;
            }

            child = m_dirs->GetNextSibling(child);
        }
    }
    else
    {
        wxTreeItemId child = m_dirs->AppendItem(target, sourceDir->GetName());
        m_dirs->SetItemData(child, sourceDir);
        m_dirs->SetItemHasChildren(child, sourceDir->HasDirectories());
        m_dirs->SelectItem(child);
        MarkDirectory(child, sourceDir);
    }

    return true;
}

// Rename a directory item
bool MainWindow::RenameDirectory(const wxTreeItemId& item, const wxString& name)
{
    Directory* itemDir = m_dirs->GetItemData(item);
    if(!itemDir)
        return false;

    m_editPanel->SetFile(NULL);

    // Real Mode
    if(IsRealMode())
    {
        if(!itemDir->CanRename(name))
            return false;
        
        wxFileName sourcefn(itemDir->GetFullPath(), wxEmptyString);
        
        if(sourcefn.DirExists())
        {
            wxFileName newname(sourcefn.GetPath(), wxEmptyString);
            newname.RemoveLastDir();
            newname.AppendDir(name);

            if(!::wxRenameFile(sourcefn.GetFullPath(), newname.GetFullPath(), false))
            {
                return false;
            }
        }
        else
        {
            return false;
        }
    }

    // Rename node
    if(!itemDir->Rename(name))
        return false;

    m_dirs->SetItemText(item, itemDir->GetName());
    MarkDirectory(item, itemDir);

    PopulateFiles(item);

    return true;
}

// Delete a directory item
bool MainWindow::DeleteDirectory(const wxTreeItemId& item)
{
    // Get parent
    wxTreeItemId parent = m_dirs->GetItemParent(item);
    if(!parent.IsOk())
        return false;

    Directory* parentDir = m_dirs->GetItemData(parent);
    if(!parentDir)
        return false;

    // Previous item
    wxTreeItemId prev = m_dirs->GetPrevSibling(item);

    // Prepare
    m_editPanel->SetFile(NULL);
    Directory* itemDir = m_dirs->GetItemData(item);
    
    // Delete node
    if(itemDir && !itemDir->Delete())
        return false;

    if(prev.IsOk())
    {
        m_dirs->SelectItem(prev);
    }
    else
    {
        m_dirs->SelectItem(parent);
    }

    m_dirs->Delete(item);
    m_dirs->SetItemHasChildren(parent, parentDir->HasDirectories());

    return true;
}

// Populate a directory
void MainWindow::PopulateDirectory(const wxTreeItemId& item)
{
    ClearDirectory(item);

    Directory* dir = m_dirs->GetItemData(item);
    if(!dir)
        return;

    DirectoryList dirs = dir->GetDirectories();
    for(DirectoryList::iterator it = dirs.begin(), end = dirs.end(); it != end; ++it)
    {
        wxTreeItemId newitem = m_dirs->AppendItem(item, (*it)->GetName());

        m_dirs->SetItemData(newitem, (*it));
        m_dirs->SetItemHasChildren(newitem, (*it)->HasDirectories());
        MarkDirectory(newitem, (*it));
    }
}

// Clear a directory
void MainWindow::ClearDirectory(const wxTreeItemId& item)
{
    Directory* dir = m_dirs->GetItemData(item);

    m_dirs->DeleteChildren(item);
    if(dir)
        m_dirs->SetItemHasChildren(item, dir->HasDirectories());
}

// Mark a directory as either existing or not
void MainWindow::MarkDirectory(const wxTreeItemId& item, Directory* dir)
{
    if(!dir)
    {
        dir = m_dirs->GetItemData(item);
        if(!dir)
            return;
    }

    if(dir->Exists())
    {
        m_dirs->SetItemImage(item, 0);
    }
    else
    {
        m_dirs->SetItemImage(item, 1);
    }
}

// Move a file
bool MainWindow::MoveFiles(const wxArrayInt& sources, const wxTreeItemId& target)
{
    Directory* targetDir = m_dirs->GetItemData(target);
    if(!targetDir)
        return false;

    m_editPanel->SetFile(NULL);

    // work backwords
    bool anything = false;
    bool realmode = IsRealMode();
    for(size_t pos = sources.Count(); pos > 0; pos--)
    {
        int index = sources[pos - 1];

        File* sourceFile = m_files->GetItemData(index);
        if(!sourceFile)
            continue;

        // Real mode
        if(realmode)
        {
            if(!sourceFile->CanMove(targetDir))
                continue;

            wxFileName sourcefn(sourceFile->GetFullPath());
            wxFileName targetfn(targetDir->GetFullPath(), wxEmptyString);

            if(sourcefn.FileExists() && targetfn.DirExists())
            {
                wxFileName newname(targetfn.GetPath(), sourcefn.GetFullName());

                if(!wxRenameFile(sourcefn.GetFullPath(), newname.GetFullPath(), false))
                {
                    continue;
                }
            }
            else
            {
                continue;
            }
        }

        // Move file node
        if(sourceFile->Move(targetDir))
        {
            anything = true;
            m_files->DeleteItem(index);
        }
    }
    
    return anything;
}

// Rename a file
bool MainWindow::RenameFile(long item, const wxString& name)
{
    File* itemFile = m_files->GetItemData(item);
    if(!itemFile)
        return false;

    m_editPanel->SetFile(NULL);

    // Real mode
    if(IsRealMode())
    {
        if(!itemFile->CanRename(name))
            return false;

        wxFileName sourcefn(itemFile->GetFullPath());

        if(sourcefn.FileExists())
        {
            wxFileName newname(sourcefn.GetPath(), name);

            if(!::wxRenameFile(sourcefn.GetFullPath(), newname.GetFullPath(), false))
            {
                return false;
            }
        }
        else
        {
            return false;
        }
    }

    // Rename node
    if(!itemFile->Rename(name))
        return false;

    m_files->SetItemText(item, itemFile->GetName());
    MarkFile(item, itemFile);
    return true;
}

// Delete files
bool MainWindow::DeleteFiles(const wxArrayInt& items)
{
    m_editPanel->SetFile(NULL);

    bool anything = false;
    for(size_t pos = items.Count(); pos > 0; pos--)
    {
        int index = items[pos - 1];

        File* itemFile = m_files->GetItemData(index);
        if(!itemFile)
            continue;

        // Delete node
        if(itemFile->Delete())
        {
            anything = true;
            m_files->DeleteItem(index);
        }
    }

    return anything;
}

// Populate file list
void MainWindow::PopulateFiles(const wxTreeItemId& item)
{
    ClearFiles();

    Directory* dir = m_dirs->GetItemData(item);
    if(!dir)
        return;

    FileList files = dir->GetFiles();
    long pos = 0;
    for(FileList::iterator it = files.begin(), end = files.end(); it != end; ++it)
    {
        m_files->InsertItem(pos, (*it)->GetName());
        m_files->SetItemData(pos, (*it));
        MarkFile(pos, (*it));
        pos++;
    }
}

// Clear the file list
void MainWindow::ClearFiles()
{
    m_editPanel->SetFile(NULL);
    m_files->DeleteAllItems();
}

// Mark a file as existing or not
void MainWindow::MarkFile(long item, File* file)
{
    if(!file)
    {
        file = m_files->GetItemData(item);
        if(!file)
            return;
    }

    if(file->Exists())
    {
        m_files->SetItemImage(item, 0);
    }
    else
    {
        m_files->SetItemImage(item, 1);
    }
}

// Get selected files
wxArrayInt MainWindow::GetSelectedFiles()
{
    wxArrayInt results;

    int index = m_files->GetFirstSelected();
    while(index != wxNOT_FOUND)
    {
        results.Add(index);
        index = m_files->GetNextSelected(index);
    }

    return results;
}

