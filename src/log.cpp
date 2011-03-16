// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>

#include "actions.h"
#include "log.h"


// Constructor
Log::Log(wxWindow* parent, wxWindowID id)
{
    Create(parent, id, wxEmptyString, wxDefaultPosition, wxDefaultSize,
        wxTE_MULTILINE | wxTE_READONLY | wxTE_DONTWRAP | wxTE_AUTO_SCROLL | wxTE_RICH | wxBORDER_SUNKEN);
}

// Clear the log
void Log::Clear()
{
    wxTextCtrl::Clear();
}

// Log a message
void Log::LogMessage(const wxString& message, bool important)
{
    // TODO: what if the text background is red or blue?
    if(important)
    {
        SetDefaultStyle(wxTextAttr(*wxRED));
    }
    else
    {
        SetDefaultStyle(wxTextAttr(*wxBLUE));
    }

    AppendText(message);
    AppendText(wxT("\n"));
};


