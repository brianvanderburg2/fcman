// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_EDITPANEL_H
#define __FCMAN_EDITPANEL_H


// Requirements
#include <wx/defs.h>
#include <wx/panel.h>
#include <wx/string.h>


class WXDLLIMPEXP_CORE wxCommandEvent;
class WXDLLIMPEXP_CORE wxStaticText;
class WXDLLIMPEXP_CORE wxTextCtrl;

template <typename T> class ListBox;
class File;
class Package;
class Dependency;


// Editor panel class
class EditPanel : public wxPanel
{
public:
    // ctor/dtor/
    EditPanel(wxWindow* parent);
    ~EditPanel();

    // Set the active file
    void SetFile(File* file);

    // Package events
    void OnPackageSelected(wxCommandEvent& evt);
    void OnPackageAdd(wxCommandEvent& evt);
    void OnPackageRemove(wxCommandEvent& evt);
    void OnPackageName(wxCommandEvent& evt);
    void OnPackageVersion(wxCommandEvent& evt);

    // Dependency events
    void OnDependencySelected(wxCommandEvent& evt);
    void OnDependencyAdd(wxCommandEvent& evt);
    void OnDependencyRemove(wxCommandEvent& evt);
    void OnDependencyName(wxCommandEvent& evt);
    void OnDependencyMinVersion(wxCommandEvent& evt);
    void OnDependencyMaxVersion(wxCommandEvent& evt);

    // Description events
    void OnDescription(wxCommandEvent& evt);

private:
    // Create the gui
    void CreateWidgets();
    wxPanel* CreateInfoPanel(wxWindow* parent);
    wxPanel* CreatePackagesPanel(wxWindow* parent);
    wxPanel* CreateDependenciesPanel(wxWindow* parent);

    void Load();

    // Enable the package/dependency
    void LoadPackage(Package* package);
    void LoadDependency(Dependency* depends);
    
    // Controls
    wxTextCtrl* m_checksum;
    wxTextCtrl* m_description;

    ListBox<Package>* m_packages;
    wxTextCtrl* m_packageName;
    wxTextCtrl* m_packageVersion;

    ListBox<Dependency>* m_dependencies;
    wxTextCtrl* m_dependencyName;
    wxTextCtrl* m_dependencyMinVersion;
    wxTextCtrl* m_dependencyMaxVersion;

    // Active file
    File* m_file;

DECLARE_EVENT_TABLE();
};



#endif // Header guard



