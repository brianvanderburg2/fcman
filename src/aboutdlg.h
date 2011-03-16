// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_ABOUTDLG_H
#define __FCMAN_ABOUTDLG_H


// Requirements
#include "config.h"

#include <wx/defs.h>
#include <wx/dialog.h>


// About dialog
class AboutDialog : public wxDialog
{
public:
    // ctor/dtor
    AboutDialog(wxWindow* parent);
    ~AboutDialog();

    // events
    void OnDetails(wxCommandEvent& evt);

private:
    void CreateWidgets();

DECLARE_EVENT_TABLE()
};


#endif // Header guard



