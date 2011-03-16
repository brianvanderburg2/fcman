// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include "config.h"

#include <wx/defs.h>
#include <wx/button.h>
#include <wx/filename.h>
#include <wx/hyperlink.h>
#include <wx/intl.h>
#include <wx/notebook.h>
#include <wx/panel.h>
#include <wx/sizer.h>
#include <wx/statbmp.h>
#include <wx/stattext.h>
#include <wx/string.h>
#include <wx/textctrl.h>
#include <wx/utils.h>


#include "app.h"
#include "aboutdlg.h"


// Details dialog
//----------------------------------------------------------------------------
namespace
{

class AboutDetailsDialog : public wxDialog
{
public:
    // ctor/dtor
    AboutDetailsDialog(wxWindow* parent);
    ~AboutDetailsDialog();

private:
    void CreateWidgets();
    void AddTextPage(wxNotebook* book, const wxString& name, const wxString& file);

};

// Constructor
AboutDetailsDialog::AboutDetailsDialog(wxWindow* parent)
{
    if(!wxDialog::Create(parent, wxID_ANY, _("Details")))
        return;

    CreateWidgets();
    CenterOnParent(wxBOTH);
}

// Destructor
AboutDetailsDialog::~AboutDetailsDialog()
{
}

// Create the widgets
void AboutDetailsDialog::CreateWidgets()
{
    wxBusyCursor busy;

    // Create notebook
    wxNotebook* notebook = new wxNotebook(this, wxID_ANY);

    // Load pages
    AddTextPage(notebook, _("License"), wxT("license.txt"));
    AddTextPage(notebook, _("GPL"), wxT("copying.txt"));
    AddTextPage(notebook, _("Authors"), wxT("authors.txt"));
    AddTextPage(notebook, _("Credits"), wxT("credits.txt"));
    AddTextPage(notebook, _("Changes"), wxT("changes.txt"));

    // Plate it
    wxBoxSizer* topSizer = new wxBoxSizer(wxVERTICAL);
    topSizer->Add(notebook, wxSizerFlags(1).Expand().DoubleBorder());

    wxSizer* buttons = CreateSeparatedButtonSizer(wxOK);
    if(buttons)
    {
        topSizer->Add(buttons, wxSizerFlags(0).Expand().DoubleBorder(wxALL - wxTOP));
    }

    SetSizerAndFit(topSizer);
}

// Add the text page
void AboutDetailsDialog::AddTextPage(wxNotebook* notebook, const wxString& name, const wxString& file)
{
    // Panel and text control
    wxPanel* panel = new wxPanel(notebook);
    wxTextCtrl* text = new wxTextCtrl(panel, wxID_ANY, wxEmptyString, wxDefaultPosition,
        wxSize(600, 400), wxTE_MULTILINE | wxTE_READONLY | wxTE_DONTWRAP | wxBORDER_SUNKEN);

    // Fixed font
    wxFont curFont = text->GetFont();
    wxFont fixedFont(curFont.GetPointSize(), wxFONTFAMILY_MODERN, curFont.GetStyle(), curFont.GetWeight());
    if(fixedFont.IsOk())
        text->SetFont(fixedFont);

    // Add it
    wxBoxSizer* sizer = new wxBoxSizer(wxVERTICAL);
    sizer->Add(text, wxSizerFlags(1).Expand().Border());
    panel->SetSizer(sizer);

    // Add the page
    notebook->AddPage(panel, name);

    // Load the contents
    wxString docfile = wxGetApp().GetDocPath(file);
    
    if(wxFileName::FileExists(docfile))
    {
        text->LoadFile(docfile);
    }
    else
    {
        text->SetValue(wxString::Format(_("Unable to load file: %s"), docfile.c_str()));
    }
}


} // Private namespace


// About dialog
//----------------------------------------------------------------------------

// Identifiers
enum
{
    ID_DETAILS = wxID_HIGHEST + 1
};

// Event table
BEGIN_EVENT_TABLE(AboutDialog, wxDialog)
    EVT_BUTTON(ID_DETAILS, AboutDialog::OnDetails)
END_EVENT_TABLE()

// Constructor
AboutDialog::AboutDialog(wxWindow* parent)
{
    if(!wxDialog::Create(parent, wxID_ANY, _("About")))
        return;

    CreateWidgets();
    CenterOnParent(wxBOTH);
}

// Destructor
AboutDialog::~AboutDialog()
{
}

// Show details
void AboutDialog::OnDetails(wxCommandEvent& WXUNUSED(evt))
{
    AboutDetailsDialog dlg(this);
    dlg.ShowModal();
}

// Create widgets
void AboutDialog::CreateWidgets()
{
    wxBusyCursor busy;

    wxBoxSizer* aboutSizer = new wxBoxSizer(wxHORIZONTAL);

    // Icon on left
#if wxUSE_STATBMP
    wxBitmap bmp;
    if(bmp.IsOk())
    {
        aboutSizer->Add(new wxStaticBitmap(this, wxID_ANY, bmp),
            wxSizerFlags().Border(wxRIGHT));
    }
#endif

    // Text on the right
    wxBoxSizer* textSizer = new wxBoxSizer(wxVERTICAL);

    textSizer->Add(new wxStaticText(this, wxID_ANY, wxT(APP_DISPLAY_NAME " " APP_VERSION)),
        wxSizerFlags(0).Left().Border(wxBOTTOM));

    textSizer->Add(new wxStaticText(this, wxID_ANY, wxT(APP_DESCRIPTION)),
        wxSizerFlags(0).Left().Border(wxBOTTOM));

    textSizer->Add(new wxStaticText(this, wxID_ANY, wxT(APP_COPYRIGHT)),
        wxSizerFlags(0).Left().Border(wxBOTTOM));

    textSizer->Add(new wxHyperlinkCtrl(this, wxID_ANY, wxT(APP_WEBSITE), wxT(APP_WEBSITE)),
        wxSizerFlags(0).Left().DoubleBorder(wxBOTTOM));

    textSizer->Add(new wxButton(this, ID_DETAILS, _("Details")),
        wxSizerFlags(0).Center().DoubleBorder(wxBOTTOM));

    aboutSizer->Add(textSizer, wxSizerFlags(1).Expand());

    // Put it on the top
    wxBoxSizer* topSizer = new wxBoxSizer(wxVERTICAL);

    topSizer->Add(aboutSizer, wxSizerFlags(1).Expand().Border());

    wxSizer* buttons = CreateSeparatedButtonSizer(wxOK);
    if(buttons)
    {
        topSizer->Add(buttons, wxSizerFlags(0).Expand().DoubleBorder(wxALL - wxTOP));
    }

    SetSizerAndFit(topSizer);
}



