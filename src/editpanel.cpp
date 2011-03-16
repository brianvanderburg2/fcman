// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/button.h>
#include <wx/gbsizer.h>
#include <wx/intl.h>
#include <wx/notebook.h>
#include <wx/panel.h>
#include <wx/sizer.h>
#include <wx/stattext.h>
#include <wx/string.h>
#include <wx/textctrl.h>
#include <wx/utils.h>

#include "editpanel.h"
#include "listbox.h"
#include "collection/collection.h"

// IDs
enum
{
    ID_PACKAGES = wxID_HIGHEST + 1,
    ID_PACKAGE_ADD,
    ID_PACKAGE_REMOVE,
    ID_PACKAGE_NAME,
    ID_PACKAGE_VERSION,
    ID_DEPENDENCIES,
    ID_DEPENDENCY_ADD,
    ID_DEPENDENCY_REMOVE,
    ID_DEPENDENCY_NAME,
    ID_DEPENDENCY_MINVERSION,
    ID_DEPENDENCY_MAXVERSION,
    ID_DESCRIPTION
};


// Event table
BEGIN_EVENT_TABLE(EditPanel, wxPanel)
    EVT_LISTBOX(ID_PACKAGES, EditPanel::OnPackageSelected)
    EVT_BUTTON(ID_PACKAGE_ADD, EditPanel::OnPackageAdd)
    EVT_BUTTON(ID_PACKAGE_REMOVE, EditPanel::OnPackageRemove)
    EVT_TEXT(ID_PACKAGE_NAME, EditPanel::OnPackageName)
    EVT_TEXT(ID_PACKAGE_VERSION, EditPanel::OnPackageVersion)

    EVT_LISTBOX(ID_DEPENDENCIES, EditPanel::OnDependencySelected)
    EVT_BUTTON(ID_DEPENDENCY_ADD, EditPanel::OnDependencyAdd)
    EVT_BUTTON(ID_DEPENDENCY_REMOVE, EditPanel::OnDependencyRemove)
    EVT_TEXT(ID_DEPENDENCY_NAME, EditPanel::OnDependencyName)
    EVT_TEXT(ID_DEPENDENCY_MINVERSION, EditPanel::OnDependencyMinVersion)
    EVT_TEXT(ID_DEPENDENCY_MAXVERSION, EditPanel::OnDependencyMaxVersion)
    
    EVT_TEXT(ID_DESCRIPTION, EditPanel::OnDescription)
END_EVENT_TABLE()


// Constructor
EditPanel::EditPanel(wxWindow* parent) :
    wxPanel(parent),
    m_checksum(NULL),
    m_description(NULL),
    m_packages(NULL),
    m_packageName(NULL),
    m_packageVersion(NULL),
    m_dependencies(NULL),
    m_dependencyName(NULL),
    m_dependencyMinVersion(NULL),
    m_dependencyMaxVersion(NULL),
    m_file(NULL)
{
    CreateWidgets();
    SetFile(NULL);
}

// Destructor
EditPanel::~EditPanel()
{
    m_file = NULL;
}


// Set the active file
void EditPanel::SetFile(File* file)
{
    m_file = file;
    Load();
}

// A package was selected
void EditPanel::OnPackageSelected(wxCommandEvent& evt)
{
    if(evt.IsSelection())
    {
        int selection = evt.GetSelection();
        Package* data = m_packages->GetItemData(selection);
        if(data)
        {
            LoadPackage(data);
            return;
        }
    }

    LoadPackage(NULL);
}

// Add a new package
void EditPanel::OnPackageAdd(wxCommandEvent& WXUNUSED(evt))
{
    if(!m_file)
        return;

    // Create package
    Package* p = new Package();
    p->SetName(wxT("untitled"));
    m_file->AddPackage(p);

    // Add to control
    int item = m_packages->Append(p->GetDisplayString());
    m_packages->SetItemData(item, p);
    m_packages->Select(item);

    LoadPackage(p);
}

// Remove selected package
void EditPanel::OnPackageRemove(wxCommandEvent& WXUNUSED(evt))
{
    int item = m_packages->GetSelection();
    if(item == wxNOT_FOUND)
        return;

    LoadPackage(NULL);

    Package* data = m_packages->GetItemData(item);
    if(data)
        data->Delete();
    m_packages->Delete(item);
}

// Package name changed
void EditPanel::OnPackageName(wxCommandEvent& WXUNUSED(evt))
{
    int item = m_packages->GetSelection();
    if(item == wxNOT_FOUND)
        return;

    wxString name = m_packageName->GetValue();
    Package* data = m_packages->GetItemData(item);
    if(!data)
        return;

    data->SetName(name);
    m_packages->SetString(item, data->GetDisplayString());
}

// Package version changed
void EditPanel::OnPackageVersion(wxCommandEvent& WXUNUSED(evt))
{
    int item = m_packages->GetSelection();
    if(item == wxNOT_FOUND)
        return;

    wxString version = m_packageVersion->GetValue();
    Package* data = m_packages->GetItemData(item);
    if(!data)
        return;

    data->SetVersion(version);
    m_packages->SetString(item, data->GetDisplayString());
}

// A dependency was selected
void EditPanel::OnDependencySelected(wxCommandEvent& evt)
{
    if(evt.IsSelection())
    {
        int selection = evt.GetSelection();
        Dependency* data = m_dependencies->GetItemData(selection);
        if(data)
        {
            LoadDependency(data);
            return;
        }
    }

    LoadDependency(NULL);
}

// Add a dependency
void EditPanel::OnDependencyAdd(wxCommandEvent& WXUNUSED(evt))
{
    if(!m_file)
        return;

    // Create dependency
    Dependency* d = new Dependency();
    d->SetName(wxT("untitled"));
    m_file->AddDependency(d);

    // Add to control
    int item = m_dependencies->Append(d->GetDisplayString());
    m_dependencies->SetItemData(item, d);
    m_dependencies->Select(item);

    LoadDependency(d);
}

// Remove a dependency
void EditPanel::OnDependencyRemove(wxCommandEvent& WXUNUSED(evt))
{
    int item = m_dependencies->GetSelection();
    if(item == wxNOT_FOUND)
        return;

    LoadDependency(NULL);

    Dependency* data = m_dependencies->GetItemData(item);
    if(data)
        data->Delete();
    m_dependencies->Delete(item);
}

// Dependency name changed
void EditPanel::OnDependencyName(wxCommandEvent& WXUNUSED(evt))
{
    int item = m_dependencies->GetSelection();
    if(item == wxNOT_FOUND)
        return;

    wxString name = m_dependencyName->GetValue();
    Dependency* data = m_dependencies->GetItemData(item);
    if(!data)
        return;

    data->SetName(name);
    m_dependencies->SetString(item, data->GetDisplayString());
}

// Dependency minimum version changed
void EditPanel::OnDependencyMinVersion(wxCommandEvent& WXUNUSED(evt))
{
    int item = m_dependencies->GetSelection();
    if(item == wxNOT_FOUND)
        return;

    wxString version = m_dependencyMinVersion->GetValue();
    Dependency* data = m_dependencies->GetItemData(item);
    if(!data)
        return;

    data->SetMinVersion(version);
    m_dependencies->SetString(item, data->GetDisplayString());
}

// Dependency maximum version changed
void EditPanel::OnDependencyMaxVersion(wxCommandEvent& WXUNUSED(evt))
{
    int item = m_dependencies->GetSelection();
    if(item == wxNOT_FOUND)
        return;

    wxString version = m_dependencyMaxVersion->GetValue();
    Dependency* data = m_dependencies->GetItemData(item);
    if(!data)
        return;

    data->SetMaxVersion(version);
    m_dependencies->SetString(item, data->GetDisplayString());
}

// Description changed
void EditPanel::OnDescription(wxCommandEvent& WXUNUSED(evt))
{
    if(m_file)
        m_file->SetDescription(m_description->GetValue());
}


// Create gui
void EditPanel::CreateWidgets()
{
    wxBusyCursor busy;

    // Book control
    wxNotebook* book = new wxNotebook(this, wxID_ANY);
    book->AddPage(CreateInfoPanel(book), _("General"));
    book->AddPage(CreatePackagesPanel(book), _("Packages"));
    book->AddPage(CreateDependenciesPanel(book), _("Dependencies"));

    // Layout
    wxBoxSizer* topSizer = new wxBoxSizer(wxVERTICAL);
    topSizer->Add(book, wxSizerFlags(1).Expand());
    SetSizerAndFit(topSizer);
}

// Create information panel
wxPanel* EditPanel::CreateInfoPanel(wxWindow* parent)
{
    wxPanel* panel = new wxPanel(parent, wxID_ANY);

    // Controls
    m_checksum = new wxTextCtrl(panel, wxID_ANY, wxEmptyString, wxDefaultPosition, wxDefaultSize,
        wxTE_READONLY | wxTE_DONTWRAP | wxBORDER_SUNKEN);
    m_description = new wxTextCtrl(panel, ID_DESCRIPTION, wxEmptyString, wxDefaultPosition, wxDefaultSize,
        wxTE_MULTILINE | wxTE_AUTO_SCROLL | wxTE_RICH | wxBORDER_SUNKEN);

    // Layout
    wxBoxSizer* panelSizer = new wxBoxSizer(wxVERTICAL);

    panelSizer->Add(new wxStaticText(panel, wxID_ANY, _("Checksum")),
        wxSizerFlags(0).Expand().Border());
    panelSizer->Add(m_checksum, wxSizerFlags(0).Expand().Border(wxALL - wxTOP));

    panelSizer->Add(new wxStaticText(panel, wxID_ANY, _("Description")),
        wxSizerFlags(0).Expand().Border());
    panelSizer->Add(m_description, wxSizerFlags(1).Expand().Border(wxALL - wxTOP));

    panel->SetSizerAndFit(panelSizer);

    return panel;
}

// Packages panel
wxPanel* EditPanel::CreatePackagesPanel(wxWindow* parent)
{
    wxPanel* panel = new wxPanel(parent, wxID_ANY);

    // Packages
    m_packages = new ListBox<Package>(panel, ID_PACKAGES, wxLB_SINGLE | wxBORDER_SUNKEN);
    wxButton* packageAdd = new wxButton(panel, ID_PACKAGE_ADD, _("Add"));
    wxButton* packageRemove = new wxButton(panel, ID_PACKAGE_REMOVE, _("Remove"));
    m_packageName = new wxTextCtrl(panel, ID_PACKAGE_NAME, wxEmptyString, wxDefaultPosition,
        wxDefaultSize, wxBORDER_SUNKEN);
    m_packageVersion = new wxTextCtrl(panel, ID_PACKAGE_VERSION, wxEmptyString, wxDefaultPosition,
        wxDefaultSize, wxBORDER_SUNKEN);
    
    // Layout
    wxBoxSizer* buttonSizer = new wxBoxSizer(wxHORIZONTAL);
    buttonSizer->Add(packageAdd, wxSizerFlags(1).Center().Border(wxRIGHT));
    buttonSizer->Add(packageRemove, wxSizerFlags(1).Center().Border(wxLEFT));

    wxStaticBoxSizer* listSizer = new wxStaticBoxSizer(wxVERTICAL, panel, _("Packages"));
    listSizer->Add(m_packages, wxSizerFlags(1).Expand().Border());
    listSizer->Add(buttonSizer, wxSizerFlags(0).Expand().Border(wxALL - wxTOP));

    wxStaticBoxSizer* inputSizer = new wxStaticBoxSizer(wxVERTICAL, panel, _("Details"));

    inputSizer->Add(new wxStaticText(panel, wxID_ANY, _("Name")),
        wxSizerFlags().Expand().Border(wxALL - wxBOTTOM));
    inputSizer->Add(m_packageName, wxSizerFlags().Expand().Border(wxALL - wxTOP));

    inputSizer->Add(new wxStaticText(panel, wxID_ANY, _("Version")),
        wxSizerFlags().Expand().Border(wxALL - wxBOTTOM));
    inputSizer->Add(m_packageVersion, wxSizerFlags().Expand().Border(wxALL - wxTOP));


    // Put them together
    wxBoxSizer* panelSizer = new wxBoxSizer(wxHORIZONTAL);
    panelSizer->Add(listSizer, wxSizerFlags(1).Expand().Border());
    panelSizer->Add(inputSizer, wxSizerFlags(1).Expand().Border(wxALL - wxLEFT));
    panel->SetSizerAndFit(panelSizer);

    return panel;
}

// Dependencies panel
wxPanel* EditPanel::CreateDependenciesPanel(wxWindow* parent)
{
    wxPanel* panel = new wxPanel(parent, wxID_ANY);

    // Dependencies
    m_dependencies = new ListBox<Dependency>(panel, ID_DEPENDENCIES, wxLB_SINGLE | wxBORDER_SUNKEN);
    wxButton* dependencyAdd = new wxButton(panel, ID_DEPENDENCY_ADD, _("Add"));
    wxButton* dependencyRemove = new wxButton(panel, ID_DEPENDENCY_REMOVE, _("Remove"));
    m_dependencyName = new wxTextCtrl(panel, ID_DEPENDENCY_NAME, wxEmptyString, wxDefaultPosition,
        wxDefaultSize, wxBORDER_SUNKEN);
    m_dependencyMinVersion = new wxTextCtrl(panel, ID_DEPENDENCY_MINVERSION, wxEmptyString, wxDefaultPosition,
        wxDefaultSize, wxBORDER_SUNKEN);
    m_dependencyMaxVersion = new wxTextCtrl(panel, ID_DEPENDENCY_MAXVERSION, wxEmptyString, wxDefaultPosition,
        wxDefaultSize, wxBORDER_SUNKEN);
    
    // Layout
    wxBoxSizer* buttonSizer = new wxBoxSizer(wxHORIZONTAL);
    buttonSizer->Add(dependencyAdd, wxSizerFlags(1).Center().Border(wxRIGHT));
    buttonSizer->Add(dependencyRemove, wxSizerFlags(1).Center().Border(wxLEFT));

    wxStaticBoxSizer* listSizer = new wxStaticBoxSizer(wxVERTICAL, panel, _("Dependencies"));
    listSizer->Add(m_dependencies, wxSizerFlags(1).Expand().Border());
    listSizer->Add(buttonSizer, wxSizerFlags(0).Expand().Border(wxALL - wxTOP));

    wxStaticBoxSizer* inputSizer = new wxStaticBoxSizer(wxVERTICAL, panel, _("Details"));

    inputSizer->Add(new wxStaticText(panel, wxID_ANY, _("Name")),
        wxSizerFlags().Expand().Border(wxALL - wxBOTTOM));
    inputSizer->Add(m_dependencyName, wxSizerFlags().Expand().Border(wxALL - wxTOP));

    inputSizer->Add(new wxStaticText(panel, wxID_ANY, _("Min Version")),
        wxSizerFlags().Expand().Border(wxALL - wxBOTTOM));
    inputSizer->Add(m_dependencyMinVersion, wxSizerFlags().Expand().Border(wxALL - wxTOP));

    inputSizer->Add(new wxStaticText(panel, wxID_ANY, _("Max Version")),
        wxSizerFlags().Expand().Border(wxALL - wxBOTTOM));
    inputSizer->Add(m_dependencyMaxVersion, wxSizerFlags().Expand().Border(wxALL - wxTOP));

    // Put them together
    wxBoxSizer* panelSizer = new wxBoxSizer(wxHORIZONTAL);
    panelSizer->Add(listSizer, wxSizerFlags(1).Expand().Border());
    panelSizer->Add(inputSizer, wxSizerFlags(1).Expand().Border(wxALL - wxLEFT));
    panel->SetSizerAndFit(panelSizer);

    return panel;
}

// Load information
void EditPanel::Load()
{
    // Reset controls
    m_checksum->ChangeValue(wxEmptyString);
    m_description->ChangeValue(wxEmptyString);

    m_packages->Clear();
    LoadPackage(NULL);

    m_dependencies->Clear();
    LoadDependency(NULL);
    

    // Enable or disable
    if(!m_file)
    {
        Enable(false);
        return;
    }

    Enable(true);

    // Update information
    m_checksum->ChangeValue(m_file->GetChecksum().Upper());
    m_description->ChangeValue(m_file->GetDescription());

    PackageList packages = m_file->GetPackages();
    for(PackageList::iterator it = packages.begin(), end = packages.end(); it != end; ++it)
    {
        int item = m_packages->Append((*it)->GetDisplayString());
        m_packages->SetItemData(item, (*it));
    }

    DependencyList dependencies = m_file->GetDependencies();
    for(DependencyList::iterator it = dependencies.begin(), end = dependencies.end(); it != end; ++it)
    {
        int item = m_dependencies->Append((*it)->GetDisplayString());
        m_dependencies->SetItemData(item, (*it));
    }

}

// Load a package
void EditPanel::LoadPackage(Package* package)
{
    if(package)
    {
        m_packageName->Enable(true);
        m_packageVersion->Enable(true);

        m_packageName->ChangeValue(package->GetName());
        m_packageVersion->ChangeValue(package->GetVersion());
    }
    else
    {
        m_packageName->ChangeValue(wxEmptyString);
        m_packageVersion->ChangeValue(wxEmptyString);

        m_packageName->Enable(false);
        m_packageVersion->Enable(false);
    }
}

// Load a dependency
void EditPanel::LoadDependency(Dependency* depends)
{
    if(depends)
    {
        m_dependencyName->Enable(true);
        m_dependencyMinVersion->Enable(true);
        m_dependencyMaxVersion->Enable(true);

        m_dependencyName->ChangeValue(depends->GetName());
        m_dependencyMinVersion->ChangeValue(depends->GetMinVersion());
        m_dependencyMaxVersion->ChangeValue(depends->GetMaxVersion());
    }
    else
    {
        m_dependencyName->ChangeValue(wxEmptyString);
        m_dependencyMinVersion->ChangeValue(wxEmptyString);
        m_dependencyMaxVersion->ChangeValue(wxEmptyString);
        
        m_dependencyName->Enable(false);
        m_dependencyMinVersion->Enable(false);
        m_dependencyMaxVersion->Enable(false);
    }
}


